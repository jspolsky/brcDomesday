#!/usr/bin/env python3
"""
Add Approved Images to Camp History

This script reads the curation results from the candidates directory
and adds approved images to the campHistory.json file.

Usage:
    python3 add_images_to_history.py

The script is idempotent - running it multiple times will replace
the images data with the current curation results.
"""

import json
from pathlib import Path

# Paths
IMAGES_DIR = Path(__file__).parent
CANDIDATES_DIR = IMAGES_DIR / "candidates"
DATA_DIR = IMAGES_DIR.parent / "data"
CAMP_HISTORY_FILE = DATA_DIR / "campHistory.json"

def load_camp_history():
    """Load the campHistory.json file."""
    with open(CAMP_HISTORY_FILE, 'r') as f:
        return json.load(f)

def save_camp_history(history):
    """Save the campHistory.json file."""
    with open(CAMP_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def get_approved_images_for_camp(camp_name):
    """
    Get all approved images for a camp from its metadata.json file.

    Returns a list of image dictionaries with url, width, height, and source_page_url.
    """
    camp_dir = CANDIDATES_DIR / camp_name
    metadata_file = camp_dir / "metadata.json"

    if not metadata_file.exists():
        return []

    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    approved_images = []

    for img in metadata.get('images', []):
        # Only include approved images
        if img.get('curation_result') == 'approved':
            approved_images.append({
                'url': img['image_url'],
                'width': img['width'],
                'height': img['height'],
                'source_page_url': img.get('source_page_url', img['image_url'])
            })

    return approved_images

def main():
    print("=" * 80)
    print("Adding Approved Images to Camp History")
    print("=" * 80)
    print()

    # Load camp history
    print(f"Loading {CAMP_HISTORY_FILE}...")
    camp_history = load_camp_history()
    print(f"Loaded {len(camp_history)} camps from history")
    print()

    # Track statistics
    camps_updated = 0
    camps_with_images_added = 0
    camps_with_images_removed = 0
    total_images_added = 0

    # Process each camp in the candidates directory
    print("Processing curated camps...")
    for camp_dir in sorted(CANDIDATES_DIR.iterdir()):
        if not camp_dir.is_dir():
            continue

        camp_name = camp_dir.name

        # Get approved images
        approved_images = get_approved_images_for_camp(camp_name)

        # Check if this camp exists in camp history
        if camp_name in camp_history:
            had_images_before = 'images' in camp_history[camp_name]
            old_image_count = len(camp_history[camp_name].get('images', []))

            if approved_images:
                # Add or update images
                camp_history[camp_name]['images'] = approved_images
                camps_updated += 1
                total_images_added += len(approved_images)

                if not had_images_before:
                    camps_with_images_added += 1
                    print(f"  ✓ {camp_name}: Added {len(approved_images)} image(s)")
                elif len(approved_images) != old_image_count:
                    print(f"  ↻ {camp_name}: Updated from {old_image_count} to {len(approved_images)} image(s)")
            else:
                # Remove images key if no approved images
                if had_images_before:
                    del camp_history[camp_name]['images']
                    camps_with_images_removed += 1
                    print(f"  ✗ {camp_name}: Removed images (was {old_image_count}, now 0 approved)")
        else:
            # Camp not in history - this might happen if it's a new camp
            # We'll skip it since campHistory.json should only contain camps with history
            if approved_images:
                print(f"  ⚠ {camp_name}: Has {len(approved_images)} approved image(s) but not in campHistory.json (skipping)")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Camps with images data updated: {camps_updated}")
    print(f"Camps with new images added: {camps_with_images_added}")
    print(f"Camps with images removed: {camps_with_images_removed}")
    print(f"Total approved images in campHistory: {total_images_added}")
    print()

    # Save updated camp history
    print(f"Saving updated campHistory.json...")
    save_camp_history(camp_history)
    print("✓ Done!")
    print("=" * 80)

if __name__ == '__main__':
    main()
