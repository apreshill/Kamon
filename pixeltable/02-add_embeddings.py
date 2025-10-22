#!/usr/bin/env python3
"""Add semantic search to Kamon using multiple embedding indexes.

This creates two types of embedding indexes:
1. CLIP on images - for visual similarity and text-to-image search
2. Sentence transformer on translations - for text semantic search

Usage:
    python 02-add_embeddings.py
"""

import pixeltable as pxt
from pixeltable.functions.huggingface import clip, sentence_transformer

# Get the table
kamon = pxt.get_table('kamon_db.kamon_images')

# Index 1: CLIP on images (multimodal - text or image queries)
kamon.add_embedding_index(
    'image',
    idx_name='clip_idx',
    embedding=clip.using(model_id='openai/clip-vit-base-patch32'),
    metric='cosine'
)

# Index 2: Sentence transformer on translations (text semantic search)
kamon.add_embedding_index(
    'translation',
    idx_name='text_idx',
    embedding=sentence_transformer.using(model_id='sentence-transformers/all-MiniLM-L6-v2'),
    metric='cosine'
)
