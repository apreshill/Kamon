# Accessing the Kamon Dataset

> **Dataset Credit**: This dataset was created and released by [Sakana AI](https://github.com/SakanaAI/Kamon). This document describes how to access and work with their dataset using Pixeltable.

The Kamon dataset from Sakana AI contains 7,410 Japanese family crests (家紋) with:
- Hand-developed descriptions in kamon terminology (家紋用語)
- Machine-generated dependency parses (Claude)
- English translations (Claude)
- Three sources: Edo period documents, Wikimedia, mon-white collection (Sakana excludes the mon-white collection from the public dataset due to licensing, but you may download it separately)

This is the only open-source kamon dataset with paired images and linguistic descriptions.

**Why Kamon**: Interpreting kamon into text (or vice versa) is hard for current vision methods due to highly stylized motifs, compositional rules, and small dataset size. Sakana AI released this dataset to encourage development of techniques that are more robust with limited but constrained data.

## Quick Start

**Install Pixeltable:**
```bash
pip install pixeltable  # Requires Python 3.10+
```

**Create table from published source:**
```python
import pixeltable as pxt

# Create local copy of the published table
kamon = pxt.create_table(
    'kamon_db.kamon_images',
    source='pxt://pixeltable:demos/kamon/kamon_images',
    if_exists='replace' # include to overwrite an existing copy
)

# Start exploring
kamon.head()
```

## What's In The Table

**Columns:**
- `image` - The kamon image (1,002 edo + wiki images)
- `description` - Japanese description (家紋用語)
- `translation` - English translation
- `parsed_expr` - Dependency parse structure
- `source` - Image source (edo, wiki, or mon_white)
- `github_url` - Direct link to source image

**Precomputed Embedding Indexes:**

This dataset includes pre-computed embedding indexes:
- `clip_idx` - CLIP embeddings on images (enables text → images and image → images search)
- `text_idx` - Sentence transformer embeddings on translations (enables text → text semantic search)

**What This Enables:**
- **Text → Images**: Search with strings to find similar images
- **Image → Images**: Use an image to find visually similar kamon
- **Text → Text**: Find conceptually similar translations
- Plus keyword search and filtering by source

## Explore the Dataset

Open **`pxt-kamon-tour.ipynb`**.

---

## For Maintainers: Rebuilding from Source

**The scripts in this directory are for recreating the published table from source data.** End users don't need to run these - just replicate the published table as shown in Quick Start above.

### Build Process

**1. Clone and Setup:**
```bash
git clone https://github.com/apreshill/Kamon.git
cd Kamon

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pixeltable transformers sentence-transformers torch
```

**2. Run Scripts in Order:**

```bash
# Make sure venv is activated
source .venv/bin/activate

# Create base table from source data (use --force to recreate if exists)
python pixeltable/01-create_table.py

# Add embedding indexes
python pixeltable/02-add_embeddings.py

# Publish to Pixeltable cloud (requires authentication)
python pixeltable/03-publish_table.py
```

### File Structure

```
pixeltable/
├── data/
│   ├── descriptions.jsonl      # Image paths and descriptions
│   ├── index_parsed_claude_all.jsonl  # Claude-parsed expressions
│   └── index_parsed_claude_all_translated_claude.jsonl  # English translations
├── 01-create_table.py         # Recreate base table from source
├── 02-add_embeddings.py       # Add embedding indexes
├── 03-publish_table.py        # Publish to cloud
├── pxt-kamon-tour.ipynb       # Exploration tutorial
├── pxt-README.md              # This file
└── pxt-requirements.txt       # Dependencies
```

### Script Details

**`01-create_table.py`** - Creates main table and intermediate tables
- Loads parsed expressions, translations, and image metadata
- Joins data and creates `kamon_db.kamon_images`
- Downloads images from GitHub URLs
- Flag: `--force` to recreate if exists

**`02-add_embeddings.py`** - Adds two embedding indexes
- `clip_idx` - CLIP on images (openai/clip-vit-base-patch32) for visual search
- `text_idx` - Sentence transformer on translations (all-MiniLM-L6-v2) for text search

**`03-publish_table.py`** - Publishes to Pixeltable cloud
- Requires authentication
- Publishes with all embeddings included

### Troubleshooting

**If you need to recreate the tables:**

```bash
# Use --force flag to drop and recreate existing tables
python pixeltable/01-create_table.py --force
python pixeltable/02-add_embeddings.py
```

### Publishing Your Fork

```bash
# Activate environment with Pixeltable 0.4.17+ (requires Python 3.10+)
source .venv/bin/activate

# Publish your tables
python pixeltable/04-publish_table.py
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
- [Pixeltable Documentation](https://docs.pixeltable.com/) - Learn more about Pixeltable

## Credits

This dataset was created and released by **Sakana AI**: [github.com/SakanaAI/Kamon](https://github.com/SakanaAI/Kamon)

**License**: [CC-BY-SA-4.0](https://github.com/SakanaAI/Kamon/blob/main/LICENSE.txt) - See Sakana AI's original license

## Support

- **Dataset questions**: See Sakana AI's [original README](README.md)
- **Pixeltable issues**: [Pixeltable GitHub](https://github.com/pixeltable/pixeltable)
