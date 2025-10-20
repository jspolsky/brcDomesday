#!/usr/bin/env python3
"""
Image Scraper for Burning Man Camp Images

This script downloads images from camp websites to build a candidate image library.
It can be interrupted and resumed at any time.

Usage:
    python scrape_images.py           # Full run
    python scrape_images.py --test    # Test mode (3 camps, 5 images each)
"""

import json
import os
import sys
import time
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

# Check for test mode
TEST_MODE = '--test' in sys.argv
TEST_CAMP_LIMIT = 10 if TEST_MODE else None
TEST_IMAGE_LIMIT_PER_CAMP = 10 if TEST_MODE else None

# Configuration
CAMP_HISTORY_PATH = Path(__file__).parent.parent.parent / "data" / "campHistory.json"
CANDIDATES_DIR = Path(__file__).parent.parent / "candidates"
STATE_FILE = Path(__file__).parent / "download_state.json"
LOG_FILE = Path(__file__).parent.parent / "candidates" / "download_log.json"

REQUEST_DELAY = 2  # Seconds between requests to same domain
MAX_IMAGES_PER_CAMP = 128
MIN_IMAGE_SIZE = 100  # pixels - smaller images are likely icons/UI
USER_AGENT = 'BRC-Domesday-Image-Scraper/1.0 (Educational project; contact: see github.com/jspolsky/brcDomesday)'

# Track social media URLs for later processing
SOCIAL_MEDIA_CAMPS = []


def load_state():
    """Load processing state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "processed_camps": [],
        "last_updated": None
    }


def save_state(state):
    """Save processing state to file."""
    state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_camp_history():
    """Load camp history data."""
    with open(CAMP_HISTORY_PATH, 'r') as f:
        return json.load(f)


def is_social_media_url(url):
    """Check if URL is from social media platforms."""
    if not url:
        return False

    url_lower = url.lower()
    social_platforms = ['facebook.com', 'instagram.com', 'twitter.com', 'x.com']
    return any(platform in url_lower for platform in social_platforms)


def collect_all_urls(camp_history_data):
    """Collect all unique URLs from camp history, grouped by camp."""
    camp_urls = {}

    for camp_name, camp_data in camp_history_data.items():
        urls = set()

        for history_entry in camp_data.get('history', []):
            url = history_entry.get('url')
            if url:
                urls.add(url)

        if urls:
            camp_urls[camp_name] = list(urls)

    return camp_urls


def is_likely_image_url(url):
    """Check if URL is likely an image based on extension."""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    parsed = urlparse(url.lower())
    return any(parsed.path.endswith(ext) for ext in image_extensions)


def extract_image_urls(html_content, base_url):
    """Extract image URLs from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    image_urls = set()

    # Find all img tags
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src:
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, src)
            if is_likely_image_url(absolute_url):
                image_urls.add(absolute_url)

    # Find all links to images
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and is_likely_image_url(href):
            absolute_url = urljoin(base_url, href)
            image_urls.add(absolute_url)

    return list(image_urls)


def download_image(image_url, output_path):
    """
    Download an image and check if it's suitable.

    Returns:
        tuple: (success: bool, width: int, height: int, size_bytes: int)
    """
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(image_url, headers=headers, timeout=30, stream=True)

        if response.status_code != 200:
            return False, 0, 0, 0

        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'image' not in content_type:
            return False, 0, 0, 0

        # Don't download videos or animations
        if 'video' in content_type or 'gif' in content_type:
            return False, 0, 0, 0

        # Read image data
        image_data = BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            image_data.write(chunk)

        image_data.seek(0)

        # Analyze image
        try:
            img = Image.open(image_data)
            width, height = img.size

            # Skip small images (likely icons/UI elements)
            if width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE:
                return False, width, height, 0

            # Save image
            image_data.seek(0)
            with open(output_path, 'wb') as f:
                f.write(image_data.read())

            size_bytes = output_path.stat().st_size
            return True, width, height, size_bytes

        except Exception as e:
            print(f"    Error analyzing image: {e}")
            return False, 0, 0, 0

    except Exception as e:
        print(f"    Error downloading image: {e}")
        return False, 0, 0, 0


def scrape_camp_images(camp_name, urls, state):
    """Scrape images for a single camp from its URLs."""
    print(f"\n{'='*80}")
    print(f"Processing: {camp_name}")
    print(f"URLs to check: {len(urls)}")

    # Create camp directory
    camp_dir = CANDIDATES_DIR / camp_name
    camp_dir.mkdir(parents=True, exist_ok=True)

    # Load or create metadata
    metadata_file = camp_dir / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {
            "camp_name": camp_name,
            "images": [],
            "urls_checked": [],
            "social_media_urls": []
        }

    total_images = len(metadata["images"])

    # Process each URL
    for url in urls:
        if url in metadata["urls_checked"]:
            print(f"  Skipping already checked URL: {url}")
            continue

        # Check if it's social media
        if is_social_media_url(url):
            print(f"  Social media URL (skipping): {url}")
            metadata["social_media_urls"].append(url)
            metadata["urls_checked"].append(url)
            if camp_name not in SOCIAL_MEDIA_CAMPS:
                SOCIAL_MEDIA_CAMPS.append(camp_name)
            continue

        print(f"  Fetching: {url}")

        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)

            if response.status_code != 200:
                print(f"    Failed: HTTP {response.status_code}")
                metadata["urls_checked"].append(url)
                continue

            # Check if we were redirected
            final_url = response.url
            if final_url != url:
                print(f"    Redirected to: {final_url}")

            # Extract image URLs using the final URL as the base
            image_urls = extract_image_urls(response.text, final_url)
            print(f"    Found {len(image_urls)} image URLs")

            # Download images
            image_limit = TEST_IMAGE_LIMIT_PER_CAMP if TEST_MODE else len(image_urls)
            for img_url in image_urls[:image_limit]:
                max_images = TEST_IMAGE_LIMIT_PER_CAMP if TEST_MODE else MAX_IMAGES_PER_CAMP
                if total_images >= max_images:
                    print(f"    Reached limit of {max_images} images")
                    break

                # Check if already downloaded
                already_downloaded = any(
                    img['image_url'] == img_url for img in metadata["images"]
                )
                if already_downloaded:
                    continue

                # Generate filename
                image_num = len(metadata["images"]) + 1
                ext = os.path.splitext(urlparse(img_url).path)[1] or '.jpg'
                filename = f"image_{image_num:05d}{ext}"
                output_path = camp_dir / filename

                print(f"    Downloading image {image_num}: {img_url[:80]}...")
                success, width, height, size_bytes = download_image(img_url, output_path)

                if success:
                    print(f"      ✓ Saved: {width}x{height}, {size_bytes} bytes")
                    metadata["images"].append({
                        "filename": filename,
                        "image_url": img_url,
                        "source_page_url": final_url,  # Use final URL after redirects
                        "original_url": url,  # Keep original URL too
                        "width": width,
                        "height": height,
                        "size_bytes": size_bytes,
                        "download_date": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    total_images += 1
                else:
                    print(f"      ✗ Skipped (too small or invalid)")

                # Rate limiting
                time.sleep(0.5)

            metadata["urls_checked"].append(url)

            # Save metadata after each URL
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            print(f"    Error processing URL: {e}")
            metadata["urls_checked"].append(url)

        # Rate limiting between URLs
        time.sleep(REQUEST_DELAY)

        if total_images >= MAX_IMAGES_PER_CAMP:
            break

    # Final save
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\nCompleted {camp_name}: {total_images} images downloaded")
    return total_images


def main():
    """Main scraper function."""
    print("="*80)
    if TEST_MODE:
        print("BRC Domesday Image Scraper - TEST MODE")
        print(f"Testing on {TEST_CAMP_LIMIT} camps, {TEST_IMAGE_LIMIT_PER_CAMP} images max each")
    else:
        print("BRC Domesday Image Scraper")
    print("="*80)
    print()

    # Load camp history
    print("Loading camp history...")
    camp_history = load_camp_history()
    camp_urls = collect_all_urls(camp_history)
    print(f"Found {len(camp_urls)} camps with URLs")

    # Load state
    state = load_state()
    print(f"Previously processed: {len(state['processed_camps'])} camps")

    # Create candidates directory
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)

    # Process camps
    if TEST_MODE:
        # In test mode, only process first N camps that haven't been processed
        camps_to_process = []
        for camp_name, urls in camp_urls.items():
            if camp_name not in state['processed_camps']:
                camps_to_process.append((camp_name, urls))
            if len(camps_to_process) >= TEST_CAMP_LIMIT:
                break
        camp_items = camps_to_process
    else:
        camp_items = list(camp_urls.items())

    total_camps = len(camp_items)
    processed_count = 0

    try:
        for camp_name, urls in camp_items:
            if camp_name in state['processed_camps']:
                continue

            processed_count += 1
            print(f"\n[{processed_count}/{total_camps}]")

            images_downloaded = scrape_camp_images(camp_name, urls, state)

            # Mark as processed
            state['processed_camps'].append(camp_name)
            save_state(state)

    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("Interrupted by user")
        print("="*80)
        save_state(state)

    # Save social media camps list
    if SOCIAL_MEDIA_CAMPS:
        social_media_file = Path(__file__).parent / "social_media_camps.json"
        with open(social_media_file, 'w') as f:
            json.dump({
                "camps_with_social_media_urls": sorted(SOCIAL_MEDIA_CAMPS),
                "count": len(SOCIAL_MEDIA_CAMPS)
            }, f, indent=2)
        print(f"\nSaved {len(SOCIAL_MEDIA_CAMPS)} camps with social media URLs")

    print("\n" + "="*80)
    print("Scraping complete!")
    print(f"Processed {len(state['processed_camps'])} camps")
    print("="*80)


if __name__ == "__main__":
    main()
