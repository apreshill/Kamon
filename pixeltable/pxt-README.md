# Accessing the Kamon Dataset

> **Dataset Credit**: This dataset was created and released by [Sakana AI](https://github.com/SakanaAI/Kamon). This document describes how to access and work with their dataset using Pixeltable.

The Kamon dataset from Sakana AI contains 7,410 Japanese family crests (家紋) with:
- Hand-developed descriptions in kamon terminology (家紋用語)
- Machine-generated dependency parses (Claude)
- English translations (Claude)
- Three sources: Edo period documents, Wikimedia, mon-white collection

This is the only open-source kamon dataset with paired images and linguistic descriptions.

**The Vision Challenge**: Interpreting kamon into text (or vice versa) is hard for current vision methods due to highly stylized motifs, compositional rules, and small dataset size. Sakana AI released this dataset to encourage development of techniques that are more robust with limited but constrained data.

## Quick Start: Access Published Dataset

The Kamon dataset is available on Pixeltable cloud:

**Replicate the table** (full copy for offline use):
```python
import pixeltable as pxt

# Replicate this table to your local environment
local_table = pxt.replicate(
    remote_uri='pxt://pixeltable:demos/kamon/kamon_images',
    local_path='my_kamon'  # Your local table name
)

# Query it
local_table.head()
local_table.where(local_table.translation.contains('moon')).collect()
```

**Fork the table** (create your own version):
```python
import pixeltable as pxt

# Get the published table
original = pxt.get_table('pxt://pixeltable:demos/kamon/kamon_images')

# Create new table with same schema
fork_table = pxt.create_table('my_kamon_fork', schema=original.schema())

# Optional: Copy existing data
fork_table.insert(original.select().collect())
```

## What You Can Do

**Step 1: Access, Explore, Share**
- Load 1,002 edo and wiki images into a queryable database (sourced from GitHub)
- Search by English (moon, crane, maple) without knowing Japanese
- Find specific images and get URLs to share
- Access all 5,540 Claude-parsed expressions and translations

**Step 2: Train ML Models**
- Create vocabulary (Japanese expressions → integer labels)
- Generate reproducible train/val/test splits (80/10/10)
- Export to PyTorch for training vision models
- Use included VGG-based baseline

## How to Do It

**What is Pixeltable?** [Pixeltable](https://github.com/pixeltable/pixeltable) is a declarative data infrastructure for multimodal AI applications. It provides a single table interface for working with images, text, video, and audio - replacing the typical patchwork of databases, file storage, and vector DBs.

### Option 1: Use Published Table (Fastest)

Replicate the pre-built table from Pixeltable cloud:

```bash
pip install pixeltable  # Requires Python 3.10+
```

```python
import pixeltable as pxt

# Replicate to your local environment
kamon = pxt.replicate(
    remote_uri='pxt://pixeltable:demos/kamon/kamon_images',
    local_path='kamon'
)

# Start querying immediately
kamon.head()
```

### Option 2: Build from Source

Create the table yourself from the GitHub repository:

```bash
# Clone the repo
git clone https://github.com/apreshill/Kamon.git
cd Kamon/pixeltable

# Install dependencies (requires Python 3.10+)
pip install -r pxt-requirements.txt

# Create the table (automatically downloads edo/wiki images from GitHub)
python 01-create_table.py
```

This creates 4 queryable Pixeltable tables:
- `kamon_db.kamon_images` - 1,002 images with translations and parsed expressions (edo + wiki from GitHub)
- `kamon_db.parsed_raw` - 5,540 Claude-parsed expressions
- `kamon_db.translations` - 5,540 English translations  
- `kamon_db.images` - 7,408 image metadata entries (intermediate table: description, path, source)

**Note**: Images from edo/ and wiki/ sources are automatically loaded from GitHub URLs. No local image files needed!

### Table Schema: kamon_db.kamon_images

**Stored Columns:**
- `description` (String) - Japanese description
- `image` (Image) - The actual image (loaded from GitHub)
- `translation` (String) - English translation
- `parsed_expr` (JSON) - Parsed expression structure
- `source` (String) - Image source (edo, wiki, or mon_white)

**Computed Column:**
- `github_url` - Original source URL (shareable)

**Accessible On-Demand:**
- `kamon.image.localpath` - Where Pixeltable cached the image locally (not stored, computed when needed)

No local file paths are stored in the table! Images are automatically downloaded from GitHub and cached locally by Pixeltable. Access the cache path only when needed using `kamon.image.localpath`.

## File Structure

```
pixeltable/
├── data/
│   ├── descriptions.jsonl      # Image paths and descriptions
│   ├── index_parsed_claude_all.jsonl  # Claude-parsed expressions
│   ├── index_parsed_claude_all_translated_claude.jsonl  # English translations
│   ├── mon-white-224/         # (Optional) Downloaded separately if needed
│   └── README.md              # Instructions for optional data
├── 01-create_table.py         # Create Pixeltable from source
├── 02-export_to_pytorch.py    # Export to PyTorch Dataset
├── 03-publish_table.py        # Publish to Pixeltable cloud
├── noising.py                 # Data augmentation utilities
├── pixeltable-tour.ipynb      # Interactive tutorial
├── pxt-README.md              # This file
└── pxt-requirements.txt       # Python dependencies
```

**Image Sources:**
- edo/ and wiki/ images: Automatically loaded from GitHub (https://github.com/apreshill/Kamon)
- mon-white-224/ images: Optional, loaded locally if directory exists

## Understanding Image Storage

### How It Works

When you create or replicate the Kamon table, here's what happens:

**1. On Table Creation:**
```python
# Images are loaded from GitHub URLs or local files
kamon.insert([{
    'image': 'https://raw.githubusercontent.com/.../img_001.png',  # URL or local path
    'description': 'イ菱',
    ...
}])
```

Pixeltable automatically:
- Downloads the image from the URL (or reads local file)
- Stores it in `~/.pixeltable/file_cache/<hash>`
- The `image` column now references that cached file

**2. On Query:**
```python
kamon.head()  # Fast! Loads from cache
```

No re-downloading needed - works offline after initial load.

**3. Accessing Image Paths:**

The table doesn't store local file paths for portability. Instead:

```python
# Access cached path on-demand (not stored as a column)
kamon.select(kamon.image.localpath, kamon.github_url).head()
# Returns: image_localpath (cached file) and github_url (source)
```

**Q: Where are my images stored?**  
A: In `~/.pixeltable/file_cache/`. Pixeltable manages this automatically.

**Q: Can I share my table?**  
A: Yes! Others will automatically download from the GitHub URLs. Cache paths are user-specific and portable.

**Q: Why not store local paths?**  
A: Portability! URLs work anywhere, local paths break when you move files. Pixeltable handles the caching seamlessly.

### Benefits of This Approach

✅ **Portable** - Works from any location  
✅ **Shareable** - Others download automatically  
✅ **Offline-capable** - Works after initial download  
✅ **Clean** - No path dependencies to manage

## Configuration

### Environment Variables

- `KAMON_GITHUB_BASE_URL`: Override the GitHub base URL for images  
  Default: `https://raw.githubusercontent.com/apreshill/Kamon/main/`  
  Use case: If you fork the repository or want to use a different source

Example:
```bash
export KAMON_GITHUB_BASE_URL="https://raw.githubusercontent.com/YOUR_USERNAME/Kamon/main/"
python 01-create_table.py
```

## Installation

### 1. Install Pixeltable

```bash
pip3 install pixeltable
```

### 2. (Optional) Install PyTorch Dependencies

Only needed if you plan to export to PyTorch for model training:

```bash
pip install -r pxt-requirements.txt
```

This installs: pixeltable, torch, torchvision, Pillow, numpy, pandas

### 3. (Optional) Download mon-white-224 Images

The `mon-white-224` dataset is not included in this package. To include these 6,425 images:

```bash
# Download and extract (from within pixeltable/ directory)
wget https://github.com/Rebolforces/kamondataset/raw/main/mon-white-224.tar.gz
tar -xzf mon-white-224.tar.gz
mkdir -p data/mon-white-224
mv train/* data/mon-white-224/
rmdir train
rm mon-white-224.tar.gz
```

Without this, you'll have ~1,000 images (Edo + Wiki). With it, you'll have the full 7,410 images.

## Step 1: Access the Images

### Create the Table

```bash
python3 pixeltable/01-create_table.py
```

This creates `kamon_db.kamon_images` with all image metadata from all sources (Edo, Wiki, mon-white).

**Options:**
- `--force`: Recreate if table exists

**Create filtered views:**
```python
import pixeltable as pxt

kamon = pxt.get_table('kamon_db.kamon_images')

# Create view excluding Edo images (recommended for training)
no_edo = pxt.create_view('kamon_db.no_edo', kamon.where(kamon.source != 'edo'))
print(f"All images: {kamon.count()}")
print(f"Without Edo: {no_edo.count()}")

# Or filter inline without creating a view
kamon.where(kamon.source != 'edo').count()
```

### The Image Table

`kamon_db.kamon_images` (also available at `pxt://pixeltable:demos/kamon/kamon_images`) contains:

| Column | What It Gives You |
|--------|-------------------|
| `image` | The kamon image |
| `description` | Japanese description (家紋用語) |
| `translation` | English translation |
| `parsed_expr` | Dependency parse from Claude |
| `github_url` | Direct link to raw image on GitHub (computed column) |
| `source` | Origin: "edo", "wiki", or "mon_white" |

**Note:** To access where Pixeltable cached an image, use `kamon.image.localpath` in your query (not stored as a column).

### Query Your Data

```python
import pixeltable as pxt

kamon = pxt.get_table('kamon_db.kamon_images')
kamon.count()  # Total images
kamon.head()   # Preview

# Count by source
print(f"Edo: {kamon.where(kamon.source == 'edo').count()}")
print(f"Wiki: {kamon.where(kamon.source == 'wiki').count()}")
print(f"Mon-white: {kamon.where(kamon.source == 'mon_white').count()}")

# Create a view for a specific source
wiki_only = pxt.create_view('kamon_db.wiki_only', kamon.where(kamon.source == 'wiki'))
wiki_only.count()
```

### Search by English Translation

Find crests by familiar concepts:

```python
# Moon crests
moon = kamon.where(kamon.translation.contains('moon'))
print(f"Found {moon.count()} moon crests")
moon.select(kamon.image, kamon.description, kamon.translation).head()

# Rabbit crests
rabbit = kamon.where(kamon.translation.contains('rabbit'))
print(f"Found {rabbit.count()} rabbit crests")
rabbit.select(kamon.image, kamon.description, kamon.translation).collect()

# Maple leaf crests
maple = kamon.where(kamon.translation.contains('maple'))
print(f"Found {maple.count()} maple crests")
maple.select(kamon.image, kamon.description, kamon.translation).collect()

# Circle patterns
circle = kamon.where(kamon.translation.contains('circle'))
circle.select(kamon.image, kamon.translation).head(10)

# Crane birds
crane = kamon.where(kamon.translation.contains('crane'))
crane.select(kamon.image, kamon.translation).collect()
```

### Discover Common Patterns

See what motifs appear most frequently:

```python
from collections import Counter

# Get all translations
translations = kamon.select(kamon.translation).collect()

# Count words
words = Counter()
for row in translations:
    if row['translation'] != 'NA':
        words.update(row['translation'].lower().replace('-', ' ').split())

# Top 20
print("Most common elements in kamon:")
for word, count in words.most_common(20):
    print(f"{word:15} {count:4} images")
```

## Step 2: Export for Training

### When You Need This

Use this when you want to train vision models to interpret kamon (image-to-text or text-to-image).

### What Happens

**First time you run `02-export_to_pytorch.py`:**
- Creates `kamon_db.vocabulary` - Maps Japanese expressions to integer labels
- Creates `kamon_db.metadata` - Stores vocab size, end token, etc.

**Every time:**
- Loads your chosen split (train/val/test)
- Applies preprocessing (resize, normalize)
- Returns PyTorch Dataset

### Usage

```bash
# Export training set with augmentations
python3 pixeltable/02-export_to_pytorch.py --division train --num_augmentations 5

# Export validation set (no augmentations)
python3 pixeltable/02-export_to_pytorch.py --division val
```

Or use directly in Python:

```python
from export_to_pytorch import PixeltableKamonDataset
from torch.utils.data import DataLoader

# Create datasets (vocabulary created automatically on first use)
train_dataset = PixeltableKamonDataset(division='train', num_augmentations=5)
val_dataset = PixeltableKamonDataset(division='val', num_augmentations=0)
test_dataset = PixeltableKamonDataset(division='test', num_augmentations=0)

# Create DataLoaders
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

# Train your model
for images, labels in train_loader:
    # images: [batch_size, 3, 224, 224] tensors
    # labels: [batch_size, max_seq_len] token IDs
    pass
```

### Additional Tables Created

**`kamon_db.vocabulary`** - Expression to label mapping

| Column | Description |
|--------|-------------|
| `expr` | Japanese expression (e.g., "丸", "に", "桜") |
| `label` | Integer label for PyTorch (0-1575) |

**`kamon_db.metadata`** - Dataset-level info

| Column | Description |
|--------|-------------|
| `key` | "vocab_size" or "end_token_id" |
| `value` | The value |

Query these tables:

```python
# View vocabulary
vocab = pxt.get_table('kamon_db.vocabulary')
vocab.head()
vocab.where(vocab.expr == '丸').collect()  # Find "circle"

# Check vocab size
meta = pxt.get_table('kamon_db.metadata')
meta.collect()
```

### Splits

Deterministic 80/10/10 splits using dataset size as random seed:
- **Train**: 80% of images
- **Val**: 10% of images
- **Test**: 10% of images

Same images in same splits every time, ensuring reproducible experiments.

## Technical Notes

### Reproducibility

- **Deterministic splits**: Uses total dataset size as random seed
- **Fixed vocabulary**: Sorted alphabetically for consistent label assignments
- **Same preprocessing**: 224x224 resize, [0.5, 0.5, 0.5] mean/std normalization
- **Compatible**: Drop-in replacement for original `kamon_dataset.py`

### When to Use Original vs. Pixeltable

**Use `kamon_dataset.py` (original):**
- Quick experiments
- Don't need to explore data
- Simpler code

**Use Pixeltable interface:**
- Need to explore the dataset
- Want reproducible splits with easy verification
- Share results with GitHub URLs
- Build production pipelines

Both produce identical outputs for training.

## Troubleshooting

### Installation Issues

On macOS, use `python3` and `pip3`:
```bash
pip3 install -r pixeltable_requirements.txt
python3 pixeltable/01-create_table.py
```

### Table Already Exists

Force recreation:
```bash
python3 pixeltable/01-create_table.py --force
```

### Missing mon-white-224 Images

The script works with just Edo and Wiki images (~1,000 total). To get all 7,410 images, download mon-white-224 as shown in Installation.

## Publishing to Pixeltable Cloud

If you create your own fork or modifications, you can publish them:

```bash
# Activate environment with Pixeltable 0.4.17+ (requires Python 3.10+)
source .venv/bin/activate

# Publish your tables
python pixeltable/03-publish_table.py
```

This publishes to `pxt://pixeltable:demos/kamon/` (requires authentication).

To publish to your own organization:
```python
import pixeltable as pxt

pxt.publish(
    source='kamon_db.kamon_images',
    destination_uri='pxt://your_org/your_dir/kamon_images',
    access='public'  # or 'private'
)
```

## Further Reading

- **[Sakana AI Kamon Repository](https://github.com/SakanaAI/Kamon)** - Original dataset release and baseline models
- [Original README](README.md) - Dataset details, training scripts, and synthetic generation
- [kamon_dataset.py](kamon_dataset.py) - Original PyTorch Dataset implementation
- [Pixeltable Documentation](https://docs.pixeltable.com/) - Learn more about Pixeltable

## Credits

This dataset was created and released by **Sakana AI**: [github.com/SakanaAI/Kamon](https://github.com/SakanaAI/Kamon)

**License**: [CC-BY-SA-4.0](https://github.com/SakanaAI/Kamon/blob/main/LICENSE.txt) - See Sakana AI's original license

The Pixeltable interface in this repository provides an alternative way to access and work with their dataset.

## Support

- **Dataset questions**: See Sakana AI's [original README](README.md)
- **Pixeltable interface**: Open an issue in this repository
- **Pixeltable issues**: [Pixeltable GitHub](https://github.com/pixeltable/pixeltable)
