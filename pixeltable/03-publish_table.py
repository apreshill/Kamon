#!/usr/bin/env python3
"""Publish Kamon table to Pixeltable cloud.

Usage:
    python 03-publish_table.py
    
Configuration:
    Set your API key in pixeltable/config.toml
"""

import os
from pathlib import Path
import pixeltable as pxt

# Try to load API key from config.toml
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python

config_path = Path(__file__).parent / 'config.toml'
if config_path.exists() and not os.getenv('PIXELTABLE_API_KEY'):
    with open(config_path, 'rb') as f:
        config = tomllib.load(f)
        api_key = config.get('pixeltable', {}).get('api_key')
        if api_key and api_key != 'your_pixeltable_api_key_here':
            os.environ['PIXELTABLE_API_KEY'] = api_key
            print(f"✓ Loaded API key from {config_path.name}")

# Publish the main kamon_images table
pxt.publish(
    source='kamon_db.kamon_images',
    destination_uri='pxt://pixeltable:demos/sakana/kamon_images',
    access='public'
)
