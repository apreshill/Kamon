#!/usr/bin/env python3
"""Create Kamon Pixeltable with separate metadata tables.

This script creates queryable tables for parsed expressions, translations, and images,
then joins them to create the final kamon_images table.

Images are loaded from GitHub URLs (edo/wiki) or local files (mon-white-224 if available).

Usage:
    python 01-create_table.py [--force]
    
Environment Variables:
    KAMON_GITHUB_BASE_URL: Base URL for GitHub images 
                           (default: https://raw.githubusercontent.com/apreshill/Kamon/main/)
"""

import os
import sys
import json
import argparse
from PIL import Image

# Configuration
ROOT = os.path.dirname(os.path.abspath(__file__))
GITHUB_BASE_URL = os.getenv(
    'KAMON_GITHUB_BASE_URL',
    'https://raw.githubusercontent.com/apreshill/Kamon/main/'
)

# Add paths
sys.path.insert(0, ROOT)

import pixeltable as pxt


# UDF for transforming analysis array (Pixeltable-native!)
@pxt.udf
def extract_expressions(analysis: list) -> list:
    """Extract 'expr' field from each item in analysis array.
    
    Transforms: [{"expr": "丸", "head": 1}, {"expr": "に", "head": -1}]
    To: ["丸", "に"]
    """
    return [item['expr'] for item in analysis]


# Parse arguments
parser = argparse.ArgumentParser(description='Create Kamon Pixeltable')
parser.add_argument('--force', action='store_true', help='Force recreation')
args = parser.parse_args()

if_exists = 'replace_force' if args.force else 'error'

# Create directory
try:
    pxt.create_dir('kamon_db')
except:
    pass

print("=" * 60)
print("Creating Kamon Pixeltable")
print("=" * 60)

# ============================================================================
# STEP 1: Load parsed expressions
# ============================================================================
print("\n[1/5] Loading parsed expressions...")

try:
    parsed = pxt.create_table('kamon_db.parsed_raw', {'data': pxt.Json}, if_exists=if_exists)
    rows = [{'data': json.loads(line)} for line in open(os.path.join(ROOT, 'data', 'index_parsed_claude_all.jsonl'))]
    parsed.insert(rows)
    print(f"  Inserted {len(rows)} rows")
    
    # Extract fields with computed columns
    parsed.add_computed_column(description=parsed.data['description'])
    parsed.add_computed_column(parsed_expr=extract_expressions(parsed.data['analysis']))
    print("  Added computed columns: description, parsed_expr")
except Exception as e:
    parsed = pxt.get_table('kamon_db.parsed_raw')
    print(f"  Table exists ({parsed.count()} rows)")

# ============================================================================
# STEP 2: Load translations
# ============================================================================
print("\n[2/5] Loading translations...")

try:
    translations = pxt.create_table(
        'kamon_db.translations',
        {'description': pxt.String, 'translation': pxt.String},
        if_exists=if_exists
    )
    # Extract only description and translation fields
    rows = []
    for line in open(os.path.join(ROOT, 'data', 'index_parsed_claude_all_translated_claude.jsonl')):
        obj = json.loads(line)
        rows.append({
            'description': obj['description'],
            'translation': obj['translation']
        })
    translations.insert(rows)
    print(f"  Inserted {len(rows)} rows")
except Exception as e:
    print(f"  Error or exists: {e}")
    translations = pxt.get_table('kamon_db.translations')
    print(f"  Table exists ({translations.count()} rows)")

# ============================================================================
# STEP 3: Flatten images array
# ============================================================================
print("\n[3/5] Flattening images...")

try:
    images = pxt.create_table(
        'kamon_db.images',
        {'description': pxt.String, 'source': pxt.String, 'path': pxt.String},
        if_exists=if_exists
    )
    
    rows = []
    for line in open(os.path.join(ROOT, 'data', 'descriptions.jsonl')):
        obj = json.loads(line)
        desc = obj['description']
        for img in obj['images']:  # Flatten array
            # Store just the path from JSONL (not resolved)
            rows.append({
                'description': desc,
                'path': img['path'],  # Keep original path from JSONL
                'source': img['source']
            })
    
    status = images.insert(rows, on_error='ignore')
    print(f"  Inserted {status.num_rows} rows, {status.num_excs} errors")
except Exception as e:
    images = pxt.get_table('kamon_db.images')
    print(f"  Table exists ({images.count()} rows)")

# ============================================================================
# STEP 4: Join tables (using Python for flexibility)
# ============================================================================
print("\n[4/5] Joining tables...")

try:
    # Get data from tables
    images_data = list(images.collect())
    parsed_data = list(parsed.select(parsed.description, parsed.parsed_expr).collect())
    trans_data = list(translations.collect())
    
    # Build lookup maps for joining
    parsed_map = {r['description']: r['parsed_expr'] for r in parsed_data}
    trans_map = {r['description']: r['translation'] for r in trans_data}
    
    print(f"  Prepared {len(images_data)} images for joining")
    
    # Create final table with image as second column
    kamon = pxt.create_table(
        'kamon_db.kamon_images',
        {
            'description': pxt.String,
            'image': pxt.Image,  # Second column for easy viewing
            'translation': pxt.String,
            'parsed_expr': pxt.Json,
            'source': pxt.String,
        },
        if_exists=if_exists
    )
    
    # Join using Python dictionaries and add image URLs
    # edo/wiki: Use GitHub URLs with proper URL encoding
    # mon-white-224: Use local paths if available
    
    # Check if mon-white-224 directory exists locally
    mon_white_exists = os.path.exists(os.path.join(ROOT, 'data', 'mon-white-224'))
    
    final_rows = []
    skipped_mon_white = 0
    
    for img_row in images_data:
        desc = img_row['description']
        path = img_row['path']  # Path from JSONL (e.g., 'data/edo/img_001.png')
        
        # Skip if not in parsed data
        if desc not in parsed_map:
            continue
        
        # Determine image source URL
        if 'mon-white-224' in path:
            if not mon_white_exists:
                skipped_mon_white += 1
                continue
            # Use local path for mon-white-224
            image_source = os.path.join(ROOT, path)
        else:
            # Use GitHub URL for edo and wiki
            # 
            # URL ENCODING NOTE:
            # Some wiki filenames contain literal '%' characters (e.g., 'Shipp%C5%8D.jpg').
            # These '%' characters must be URL-encoded as '%25' for HTTP requests to work.
            # 
            # Example:
            #   - Filename on GitHub: Shipp%C5%8D.jpg (literal % in the name)
            #   - Path from JSONL: data/wiki/Shipp%C5%8D.jpg
            #   - HTTP URL requires: data/wiki/Shipp%25C5%258D.jpg (% → %25)
            # 
            # Without this encoding, 65 wiki images would return HTTP 404.
            # With this encoding, all 1,002 images (812 edo + 190 wiki) load successfully.
            #
            # Do NOT use urllib.parse.quote() or unquote() - they will double-encode or
            # change the path. Simple string replacement is correct here.
            encoded_path = path.replace('%', '%25')
            image_source = f'{GITHUB_BASE_URL}{encoded_path}'
            
        final_rows.append({
            'description': desc,
            'image': image_source,
            'translation': trans_map.get(desc, 'NA'),
            'parsed_expr': parsed_map[desc],
            'source': img_row['source'],
        })
    
    if skipped_mon_white > 0:
        print(f"  Skipped {skipped_mon_white} mon-white-224 images (directory not found)")
        print(f"  To add them: Download tarball from https://github.com/Rebolforces/kamondataset")
        print(f"  Then extract to data/mon-white-224/ and re-run with --force")
    else:
        if mon_white_exists:
            print(f"  Included mon-white-224 images from local directory")
    
    status = kamon.insert(final_rows, on_error='ignore')
    print(f"  Inserted {status.num_rows} rows, {status.num_excs} errors")
    
    # Remove rows with image errors (keep table clean)
    if status.num_excs > 0:
        print(f"  Removing rows with image errors...")
        # Delete rows where image failed to load (Pixeltable method)
        delete_count = kamon.delete(kamon.image.errortype != None)
        print(f"  Deleted {delete_count} error rows, {kamon.count()} images remain")
except Exception as e:
    print(f"  Error during insert: {e}")
    kamon = pxt.get_table('kamon_db.kamon_images')
    print(f"  Table exists ({kamon.count()} rows)")

# ============================================================================
# STEP 5: Add computed columns
# ============================================================================
print("\n[5/5] Adding computed columns...")

# Add computed columns for file access
try:
    # GitHub URL (for edo/wiki) or file:// URL (for mon-white-224)
    kamon.add_computed_column(github_url=kamon.image.fileurl)
    print("  Added github_url (source URL)")
except Exception as e:
    print(f"  Error adding github_url: {e}")

# Note: cached_path (kamon.image.localpath) is available on-demand
# but not stored as a computed column for portability

# ============================================================================
# Done!
# ============================================================================
print("\n" + "=" * 60)
print("✓ Kamon Pixeltable Created")
print("=" * 60)
print(f"\nTables created:")
print(f"  kamon_db.parsed_raw: {parsed.count()} rows")
print(f"  kamon_db.translations: {translations.count()} rows")
print(f"  kamon_db.images: {images.count()} rows (flattened)")
print(f"  kamon_db.kamon_images: {kamon.count()} rows (final)")

print(f"\nImage sources:")
edo_wiki_count = kamon.where((kamon.source == 'edo') | (kamon.source == 'wiki')).count()
mon_white_count = kamon.where(kamon.source == 'mon_white').count()
print(f"  edo + wiki: {edo_wiki_count} (from GitHub URLs)")
if mon_white_count > 0:
    print(f"  mon-white-224: {mon_white_count} (from local files)")

# Verify no image errors remain (should be 0 after cleanup)
try:
    error_count = kamon.where(kamon.image.errortype != None).count()
    if error_count > 0:
        print(f"\n⚠️  WARNING: {error_count} images still have errors")
    else:
        print(f"\n✓ All images validated successfully")
except Exception as e:
    print(f"\n⚠️  Could not check image errors: {e}")

print("\nExplore metadata:")
print("  parsed = pxt.get_table('kamon_db.parsed_raw')")
print("  parsed.head()")
print("\nExplore images:")
print("  kamon = pxt.get_table('kamon_db.kamon_images')")
print("  kamon.head()")
