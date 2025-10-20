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
from multiprocessing import Pool, Manager
import multiprocessing

# Check for test mode
TEST_MODE = '--test' in sys.argv
TEST_CAMP_LIMIT = 5 if TEST_MODE else None
TEST_IMAGE_LIMIT_PER_CAMP = 5 if TEST_MODE else None

# Configuration
CAMP_HISTORY_PATH = Path(__file__).parent.parent.parent / "data" / "campHistory.json"
CANDIDATES_DIR = Path(__file__).parent.parent / "candidates"
STATE_FILE = Path(__file__).parent / "download_state.json"
LOG_FILE = Path(__file__).parent.parent / "candidates" / "download_log.json"

REQUEST_DELAY = 2  # Seconds between requests to same domain
MAX_IMAGES_PER_CAMP = 128
MIN_IMAGE_SIZE = 256  # pixels - minimum width AND height for quality images
MAX_PAGES_PER_SITE = 50  # Maximum number of pages to visit per website
MAX_CRAWL_DEPTH = 3  # Maximum depth to follow links (1 = only linked pages from homepage)
MAX_CONCURRENT_CAMPS = 16  # Number of camps to process in parallel
USER_AGENT = 'BRC-Domesday-Image-Scraper/1.0 (Educational project; contact: see github.com/jspolsky/brcDomesday)'

# Track social media URLs for later processing
SOCIAL_MEDIA_CAMPS = []


def load_state():
    """Load processing state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "camps": {},
        "summary": {
            "total_camps_processed": 0,
            "camps_with_images": 0,
            "camps_with_social_media_only": 0,
            "camps_with_errors": 0,
            "camps_with_no_images": 0,
            "total_images_downloaded": 0
        },
        "last_updated": None
    }


def save_state(state, lock=None):
    """Save processing state to file."""
    state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Sort camps alphabetically
    sorted_camps = dict(sorted(state["camps"].items()))
    state["camps"] = sorted_camps

    # Update summary counts
    state["summary"]["total_camps_processed"] = len(state["camps"])
    state["summary"]["camps_with_images"] = sum(1 for c in state["camps"].values() if c.get("images_downloaded", 0) > 0)
    state["summary"]["camps_with_social_media_only"] = sum(1 for c in state["camps"].values() if c.get("status") == "social_media_only")
    state["summary"]["camps_with_errors"] = sum(1 for c in state["camps"].values() if c.get("status") == "error")
    state["summary"]["camps_with_no_images"] = sum(1 for c in state["camps"].values() if c.get("status") == "no_images_found")
    state["summary"]["total_images_downloaded"] = sum(c.get("images_downloaded", 0) for c in state["camps"].values())

    if lock:
        with lock:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
    else:
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


def is_same_domain(url1, url2):
    """Check if two URLs are on the same domain."""
    domain1 = urlparse(url1).netloc.lower()
    domain2 = urlparse(url2).netloc.lower()
    # Remove 'www.' prefix for comparison
    domain1 = domain1.replace('www.', '')
    domain2 = domain2.replace('www.', '')
    return domain1 == domain2


def extract_page_links(html_content, base_url):
    """Extract all HTML page links from content (not image links)."""
    soup = BeautifulSoup(html_content, 'html.parser')
    page_links = set()

    for link in soup.find_all('a'):
        href = link.get('href')
        if not href:
            continue

        # Convert to absolute URL
        absolute_url = urljoin(base_url, href)

        # Skip if it's an image link
        if is_likely_image_url(absolute_url):
            continue

        # Skip if it's not the same domain
        if not is_same_domain(absolute_url, base_url):
            continue

        # Skip fragments and just anchors
        parsed = urlparse(absolute_url)
        if parsed.fragment and not parsed.path:
            continue

        # Remove fragment for deduplication
        clean_url = absolute_url.split('#')[0]

        # Only add HTML-like URLs
        path_lower = parsed.path.lower()
        # Skip common non-page files
        skip_extensions = ['.pdf', '.zip', '.tar', '.gz', '.doc', '.docx', '.xls', '.xlsx',
                          '.ppt', '.pptx', '.mp4', '.mov', '.avi', '.mp3', '.wav']
        if any(path_lower.endswith(ext) for ext in skip_extensions):
            continue

        page_links.add(clean_url)

    return list(page_links)


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


def crawl_site_for_images(start_url, metadata, camp_record, total_images):
    """
    Crawl a website starting from start_url, following links to discover images.

    Args:
        start_url: The URL to start crawling from
        metadata: The camp metadata dict to update
        camp_record: The camp record dict for state tracking
        total_images: Current count of images downloaded

    Returns:
        Updated total_images count
    """
    visited_pages = set()
    pages_to_visit = [(start_url, 0)]  # (url, depth)
    pages_visited_count = 0

    while pages_to_visit and pages_visited_count < MAX_PAGES_PER_SITE:
        if total_images >= MAX_IMAGES_PER_CAMP:
            break

        if TEST_MODE and total_images >= TEST_IMAGE_LIMIT_PER_CAMP:
            break

        current_url, depth = pages_to_visit.pop(0)

        # Skip if already visited
        if current_url in visited_pages:
            continue

        visited_pages.add(current_url)
        pages_visited_count += 1

        print(f"    Crawling page {pages_visited_count} (depth {depth}): {current_url[:80]}...")

        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(current_url, headers=headers, timeout=30, allow_redirects=True)

            if response.status_code != 200:
                print(f"      Failed: HTTP {response.status_code}")
                continue

            final_url = response.url
            if final_url != current_url and final_url not in visited_pages:
                visited_pages.add(final_url)

            # Extract images from this page
            image_urls = extract_image_urls(response.text, final_url)
            print(f"      Found {len(image_urls)} images on this page")

            # Download images
            for img_url in image_urls:
                max_images = TEST_IMAGE_LIMIT_PER_CAMP if TEST_MODE else MAX_IMAGES_PER_CAMP
                if total_images >= max_images:
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

                # Create camp directory if needed
                camp_dir = CANDIDATES_DIR / metadata["camp_name"]
                camp_dir.mkdir(parents=True, exist_ok=True)

                filename = f"image_{image_num:05d}{ext}"
                output_path = camp_dir / filename

                print(f"      Downloading image {image_num}: {img_url[:60]}...")
                success, width, height, size_bytes = download_image(img_url, output_path)

                if success:
                    print(f"        ✓ Saved: {width}x{height}, {size_bytes} bytes")
                    metadata["images"].append({
                        "filename": filename,
                        "image_url": img_url,
                        "source_page_url": final_url,
                        "original_url": start_url,
                        "width": width,
                        "height": height,
                        "size_bytes": size_bytes,
                        "download_date": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    total_images += 1
                else:
                    print(f"        ✗ Skipped (too small or invalid)")

                # Rate limiting between images
                time.sleep(0.5)

            # If we haven't reached max depth, extract page links to visit
            if depth < MAX_CRAWL_DEPTH:
                page_links = extract_page_links(response.text, final_url)
                print(f"      Found {len(page_links)} page links to explore")

                # Add new pages to visit queue
                for link in page_links:
                    if link not in visited_pages:
                        pages_to_visit.append((link, depth + 1))

            # Rate limiting between pages
            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"      Error crawling page: {e}")
            continue

    print(f"    Crawl complete: visited {pages_visited_count} pages, found {total_images} total images")
    return total_images


def scrape_camp_images_worker(args):
    """
    Worker function for multiprocessing.
    Takes a tuple of (camp_name, urls) and returns (camp_name, camp_record).
    """
    camp_name, urls = args
    camp_record = scrape_camp_images(camp_name, urls)
    return (camp_name, camp_record)


def scrape_camp_images(camp_name, urls):
    """Scrape images for a single camp from its URLs."""
    print(f"\n{'='*80}")
    print(f"Processing: {camp_name}")
    print(f"URLs to check: {len(urls)}")

    # Initialize camp record in state
    camp_record = {
        "urls_provided": urls,
        "urls_checked": [],
        "social_media_urls": [],
        "error_urls": [],
        "redirected_urls": {},
        "images_downloaded": 0,
        "status": None,
        "last_processed": time.strftime("%Y-%m-%d %H:%M:%S")
    }

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
            camp_record["social_media_urls"].append(url)
            camp_record["urls_checked"].append(url)
            continue

        print(f"  Starting crawl from: {url}")

        try:
            # First check if URL is accessible and handle redirects
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)

            if response.status_code != 200:
                print(f"    Failed: HTTP {response.status_code}")
                metadata["urls_checked"].append(url)
                camp_record["urls_checked"].append(url)
                camp_record["error_urls"].append({"url": url, "error": f"HTTP {response.status_code}"})
                continue

            # Check if we were redirected
            final_url = response.url
            if final_url != url:
                print(f"    Redirected to: {final_url}")
                camp_record["redirected_urls"][url] = final_url
            else:
                final_url = url

            # Crawl the site starting from this URL
            total_images = crawl_site_for_images(final_url, metadata, camp_record, total_images)

            metadata["urls_checked"].append(url)
            camp_record["urls_checked"].append(url)

            # Save metadata after each URL
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            print(f"    Error processing URL: {e}")
            metadata["urls_checked"].append(url)
            camp_record["urls_checked"].append(url)
            camp_record["error_urls"].append({"url": url, "error": str(e)})

        # Rate limiting between URLs
        time.sleep(REQUEST_DELAY)

        if total_images >= MAX_IMAGES_PER_CAMP:
            break

    # Final save
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Determine status
    camp_record["images_downloaded"] = total_images

    if len(camp_record["social_media_urls"]) > 0 and len(camp_record["urls_checked"]) == len(camp_record["social_media_urls"]):
        camp_record["status"] = "social_media_only"
    elif len(camp_record["error_urls"]) > 0 and total_images == 0:
        camp_record["status"] = "error"
    elif total_images > 0:
        camp_record["status"] = "success"
    else:
        camp_record["status"] = "no_images_found"

    print(f"\nCompleted {camp_name}: {total_images} images downloaded (status: {camp_record['status']})")
    return camp_record


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
    print(f"Previously processed: {len(state['camps'])} camps")
    if state.get('summary'):
        print(f"  - With images: {state['summary']['camps_with_images']}")
        print(f"  - Social media only: {state['summary']['camps_with_social_media_only']}")
        print(f"  - No images found: {state['summary']['camps_with_no_images']}")
        print(f"  - Errors: {state['summary']['camps_with_errors']}")
        print(f"  - Total images: {state['summary']['total_images_downloaded']}")

    # Create candidates directory
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)

    # Filter out already-processed camps
    camps_to_process = []
    for camp_name, urls in camp_urls.items():
        if camp_name not in state['camps']:
            camps_to_process.append((camp_name, urls))
        if TEST_MODE and len(camps_to_process) >= TEST_CAMP_LIMIT:
            break

    total_camps = len(camps_to_process)
    print(f"\nCamps to process: {total_camps}")

    if total_camps == 0:
        print("No camps to process!")
        return

    # Create multiprocessing lock for state file access
    manager = Manager()
    file_lock = manager.Lock()

    # Process camps in parallel
    try:
        num_workers = min(MAX_CONCURRENT_CAMPS, total_camps)
        print(f"Starting {num_workers} worker processes...\n")

        with Pool(processes=num_workers) as pool:
            # Use imap_unordered for better performance and progress tracking
            results = pool.imap_unordered(scrape_camp_images_worker, camps_to_process)

            processed_count = 0
            for camp_name, camp_record in results:
                processed_count += 1
                print(f"\n{'='*80}")
                print(f"Completed {processed_count}/{total_camps}: {camp_name}")
                print(f"{'='*80}")

                # Update state with this camp's results
                with file_lock:
                    # Reload state to get latest from other workers
                    current_state = load_state()
                    current_state['camps'][camp_name] = camp_record
                    save_state(current_state)

    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("Interrupted by user - waiting for current camps to finish...")
        print("="*80)
        pool.terminate()
        pool.join()
        # Reload final state
        state = load_state()

    # Reload final state to get accurate summary
    final_state = load_state()

    print("\n" + "="*80)
    print("Scraping complete!")
    print("="*80)
    print(f"Total camps processed: {final_state['summary']['total_camps_processed']}")
    print(f"  - With images: {final_state['summary']['camps_with_images']}")
    print(f"  - Social media only: {final_state['summary']['camps_with_social_media_only']}")
    print(f"  - No images found: {final_state['summary']['camps_with_no_images']}")
    print(f"  - Errors: {final_state['summary']['camps_with_errors']}")
    print(f"Total images downloaded: {final_state['summary']['total_images_downloaded']}")
    print("="*80)


if __name__ == "__main__":
    # Required for multiprocessing on macOS/Windows
    multiprocessing.set_start_method('spawn', force=True)
    main()
