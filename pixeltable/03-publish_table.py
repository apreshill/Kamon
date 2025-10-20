#!/usr/bin/env python3
"""Publish Kamon tables to Pixeltable cloud.

This script publishes the Kamon dataset tables to pxt://pixeltable:demos/
for public access and sharing.

Usage:
    python pixeltable/03-publish_table.py [--private]
"""

import argparse
import pixeltable as pxt

# Parse arguments
parser = argparse.ArgumentParser(description='Publish Kamon tables to Pixeltable cloud')
parser.add_argument('--private', action='store_true', help='Publish as private (default: public)')
args = parser.parse_args()

access_level = 'private' if args.private else 'public'

print("=" * 60)
print("Publishing Kamon Tables to Pixeltable Cloud")
print("=" * 60)

# Define tables to publish
tables_to_publish = [
    ('kamon_db.kamon_images', 'kamon_images'),
    ('kamon_db.parsed_raw', 'parsed_raw'),
    ('kamon_db.translations', 'translations'),
    ('kamon_db.images', 'images'),
]

# Publish all tables
for source, dest_name in tables_to_publish:
    dest_uri = f'pxt://pixeltable:demos/kamon/{dest_name}'
    print(f"Publishing {source} → {dest_uri}")
    pxt.publish(source=source, destination_uri=dest_uri, access=access_level)

print("\n" + "=" * 60)
print("✓ Complete")
print("=" * 60)
print(f"\nAccess the dataset ({access_level}):")
print("  kamon = pxt.get_table('pxt://pixeltable:demos/kamon/kamon_images')")

