#!/usr/bin/env python3
"""Export Pixeltable Kamon data to PyTorch Dataset format.

This script exports the Pixeltable data to a PyTorch-compatible Dataset
that matches the original KamonDataset interface.

Usage:
    python export_to_pytorch.py [--division train|val|test] [--num_augmentations 5]
"""

import os
import sys
import random
import argparse
from copy import deepcopy
from typing import Optional

import torch
import pixeltable as pxt
from PIL import Image
from torchvision import transforms

# Configuration
ROOT = os.path.dirname(os.path.abspath(__file__))
# Add parent directory to path to import noising module from repo root
sys.path.insert(0, os.path.dirname(ROOT))

import noising


class PixeltableKamonDataset(torch.utils.data.Dataset):
    """PyTorch Dataset wrapper for Pixeltable Kamon data.
    
    This class provides the same interface as the original KamonDataset
    but loads data from Pixeltable.
    
    Args:
        division: One of "train", "val", or "test"
        image_size: Size to resize images to (default: 224)
        dataset_mean: Mean for normalization (default: [0.5, 0.5, 0.5])
        dataset_std: Std for normalization (default: [0.5, 0.5, 0.5])
        one_hot: Whether to convert labels to one-hot encoding
        pad: Whether to pad sequences to max length
        num_augmentations: Number of augmented versions per training image (default: 5)
    """
    
    def __init__(
        self,
        division: str = "train",
        image_size: int = 224,
        dataset_mean: list = [0.5, 0.5, 0.5],
        dataset_std: list = [0.5, 0.5, 0.5],
        one_hot: bool = False,
        pad: bool = True,
        num_augmentations: int = 5,
    ):
        assert division in ["train", "val", "test"], f"Invalid division: {division}"
        
        self.division = division
        self.image_size = image_size
        self.dataset_mean = dataset_mean
        self.dataset_std = dataset_std
        self.one_hot = one_hot
        self.pad = pad
        self.num_augmentations = num_augmentations
        
        # Ensure vocabulary tables exist (created on first run)
        self._ensure_vocabulary_tables()
        
        # Load vocabulary from Pixeltable
        vocab_t = pxt.get_table('kamon_db.vocabulary')
        vocab_rows = vocab_t.select(vocab_t.expr, vocab_t.label).collect()
        
        self.expr_to_label = {row['expr']: row['label'] for row in vocab_rows}
        self.label_to_expr = {row['label']: row['expr'] for row in vocab_rows}
        
        # Load metadata
        meta_t = pxt.get_table('kamon_db.metadata')
        meta_rows = meta_t.collect()
        meta = {row['key']: row['value'] for row in meta_rows}
        
        self.vocab_size = meta['vocab_size']
        self.end_token = meta['end_token_id']
        self.max_v = len(self.expr_to_label)
        
        # Load all data from Pixeltable
        kamon = pxt.get_table('kamon_db.kamon_images')
        result = kamon.select(
            kamon.description,
            kamon.translation,
            kamon.parsed_expr,
            kamon.image.localpath,  # Access cached path on-demand
            kamon.source,
            kamon.image
        ).collect()
        
        all_rows = list(result)
        
        # Apply shuffling and splitting (same logic as kamon_dataset.py)
        total_count = len(all_rows)
        random.seed(total_count)
        indices = list(range(total_count))
        random.shuffle(indices)
        
        # Shuffle rows
        shuffled_rows = [all_rows[i] for i in indices]
        
        # Get split for this division
        train_top = int(0.8 * total_count)
        val_top = int(0.9 * total_count)
        
        if division == "train":
            subset_rows = shuffled_rows[:train_top]
        elif division == "val":
            subset_rows = shuffled_rows[train_top:val_top]
        else:  # test
            subset_rows = shuffled_rows[val_top:]
        
        # Store metadata
        self.metadata = []
        for row in subset_rows:
            # Use image from Pixeltable's cache (already downloaded and stored)
            # Note: kamon.image.localpath becomes 'image_localpath' in results (underscore, not dot)
            img_path = row['image_localpath']
            img = Image.open(img_path).convert('RGB')
            
            # Compute labels from parsed expressions
            labels = [self.expr_to_label[expr] for expr in row['parsed_expr']]
            labels.append(self.end_token)
            
            item = {
                'description': row['description'],
                'translation': row['translation'],
                'labels': labels,
                'path': row['image_localpath'],  # Reference to cached image
                'source': row['source'],
                'image': img,
            }
            self.metadata.append(item)
        
        # Calculate max length
        self.max_len = max(len(item['labels']) for item in self.metadata)
        
        # Apply augmentations for training data
        if division == "train" and num_augmentations > 0:
            print(f"Applying {num_augmentations} augmentations per training image...")
            new_train = []
            for elt in self.metadata:
                for _ in range(num_augmentations):
                    new_elt = deepcopy(elt)
                    new_elt['image'] = noising.apply_adjustments(new_elt['image'])
                    new_train.append(new_elt)
            self.metadata += new_train
            random.shuffle(self.metadata)
            print(f"Training set expanded to {len(self.metadata)} images")
        
        # Setup transforms
        self.transform = transforms.Compose([
            transforms.Resize((self.image_size, self.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(self.dataset_mean, self.dataset_std),
        ])
        
        self.padded = [self.end_token] * self.max_len
    
    def _ensure_vocabulary_tables(self):
        """Create vocabulary tables if they don't exist.
        
        WHY: PyTorch needs integer labels for training, but Pixeltable stores
        human-readable Japanese expressions. This vocabulary maps between them.
        
        HOW: 
        1. Scan all parsed_expr in the image table
        2. Create unique mapping: expression → integer label
        3. Store in vocabulary table for consistent encoding/decoding
        """
        try:
            # Check if vocabulary exists
            pxt.get_table('kamon_db.vocabulary')
            return  # Already exists
        except:
            pass
        
        print("Creating vocabulary tables for PyTorch export...")
        
        # Create vocabulary from parsed expressions
        kamon = pxt.get_table('kamon_db.kamon_images')
        all_parsed = kamon.select(kamon.parsed_expr).collect()
        
        # Collect unique expressions
        expressions = set()
        for row in all_parsed:
            for expr in row['parsed_expr']:
                expressions.add(expr)
        
        expressions = sorted(list(expressions))
        expressions.append("<EOS>")  # End of sequence token
        
        # Create vocabulary table
        vocab_t = pxt.create_table(
            'kamon_db.vocabulary',
            {'expr': pxt.String, 'label': pxt.Int}
        )
        rows = [
            {'expr': expr, 'label': idx} 
            for idx, expr in enumerate(expressions)
        ]
        vocab_t.insert(rows)
        print(f"Created vocabulary table with {len(expressions)} tokens")
        
        # Create metadata table
        meta_t = pxt.create_table(
            'kamon_db.metadata',
            {'key': pxt.String, 'value': pxt.Int}
        )
        meta_t.insert([
            {'key': 'vocab_size', 'value': len(expressions)},
            {'key': 'end_token_id', 'value': len(expressions) - 1},
        ])
        print("Created metadata table")
    
    def __len__(self):
        return len(self.metadata)
    
    def __getitem__(self, idx):
        item = self.metadata[idx]
        image = item['image']
        labels = item['labels']
        
        if self.pad:
            labels = torch.tensor((labels + self.padded)[:self.max_len])
        else:
            labels = torch.tensor(labels)
        
        if self.one_hot:
            labels = torch.nn.functional.one_hot(labels, self.max_v)
        
        return (
            self.transform(image),
            labels,
        )
    
    def dump_text(self, path: str):
        """Dumps partition in a text format, one string per line.
        
        This matches the original KamonDataset.dump_text() method.
        """
        seen = set()
        for elt in self.metadata:
            text = " ".join([self.label_to_expr[t] for t in elt['labels']])
            seen.add(text)
        with open(path, "w") as s:
            for text in seen:
                s.write(f"{text}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Export Pixeltable Kamon data to PyTorch Dataset'
    )
    parser.add_argument(
        '--division',
        type=str,
        default='train',
        choices=['train', 'val', 'test'],
        help='Dataset division to export'
    )
    parser.add_argument(
        '--num_augmentations',
        type=int,
        default=5,
        help='Number of augmentations per training image (default: 5)'
    )
    parser.add_argument(
        '--batch_size',
        type=int,
        default=16,
        help='Batch size for DataLoader'
    )
    parser.add_argument(
        '--one_hot',
        action='store_true',
        help='Convert labels to one-hot encoding'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"Exporting Kamon Pixeltable to PyTorch Dataset")
    print("=" * 60)
    print(f"Division: {args.division}")
    print(f"Augmentations: {args.num_augmentations if args.division == 'train' else 0}")
    print(f"Batch size: {args.batch_size}")
    print()
    
    try:
        # Create dataset
        dataset = PixeltableKamonDataset(
            division=args.division,
            one_hot=args.one_hot,
            num_augmentations=args.num_augmentations if args.division == 'train' else 0,
        )
        
        print(f"Dataset size: {len(dataset)} examples")
        print(f"Vocabulary size: {dataset.vocab_size}")
        print(f"Max sequence length: {dataset.max_len}")
        print()
        
        # Create DataLoader
        dataloader = torch.utils.data.DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=(args.division == 'train'),
            num_workers=4,
            pin_memory=True,
        )
        
        # Show example batch
        print("Loading example batch...")
        for batch_idx, (images, labels) in enumerate(dataloader):
            print(f"Batch shape - Images: {images.shape}, Labels: {labels.shape}")
            print(f"Example label sequence: {labels[0][:10].tolist()}...")
            break
        
        print()
        print("=" * 60)
        print("Export successful!")
        print("=" * 60)
        print("\nYou can now use PixeltableKamonDataset in your training code:")
        print()
        print("import importlib")
        print("m = importlib.import_module('02-export_to_pytorch')")
        print("train_dataset = m.PixeltableKamonDataset(division='train')")
        print()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

