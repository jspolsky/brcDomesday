#!/usr/bin/env python3
"""
Quick test of crawling on Children of Chaos website
"""

import json
import time
from pathlib import Path

# Import functions from scrape_images
import sys
sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import (
    crawl_site_for_images,
    CANDIDATES_DIR
)

def test_chaos():
    """Test crawling on Children of Chaos website."""

    camp_name = "Children of Chaos TEST"
    test_url = "https://chaoscamp.wordpress.com/"

    print("Testing crawl on Children of Chaos website")
    print(f"URL: {test_url}")
    print()

    # Create metadata structure
    metadata = {
        "camp_name": camp_name,
        "images": [],
        "urls_checked": [],
        "social_media_urls": []
    }

    # Create camp record
    camp_record = {
        "urls_provided": [test_url],
        "urls_checked": [],
        "social_media_urls": [],
        "error_urls": [],
        "redirected_urls": {},
        "images_downloaded": 0,
        "status": None,
        "last_processed": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Crawl the site
    total_images = crawl_site_for_images(test_url, metadata, camp_record, 0)

    print()
    print("="*80)
    print(f"RESULTS: Found {total_images} images")
    print(f"Crawled {len(metadata.get('pages_visited', []))} pages")
    print("="*80)

    # Show some sample image URLs
    if metadata["images"]:
        print("\nSample images found:")
        for i, img in enumerate(metadata["images"][:10]):
            print(f"  {i+1}. {img['width']}x{img['height']} - {img['image_url'][:80]}")
            print(f"     From: {img['source_page_url'][:80]}")

if __name__ == "__main__":
    test_chaos()
