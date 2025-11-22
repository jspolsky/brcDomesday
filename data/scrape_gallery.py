#!/usr/bin/env python3
"""
Burning Man Gallery Scraper

Scrapes images from gallery.burningman.org for camps in camps.json.
Downloads candidate images for curator approval.

Usage:
    python3 scrape_gallery.py [options]

Options:
    --camp "Camp Name"    # Process single camp only
    --limit N             # Process only first N camps
    --skip-existing       # Skip camps that already have gallery images
    --max-images N        # Download max N images per camp (default: 128)
    --delay SECONDS       # Override default delay between camps
    --dry-run             # Show what would be done without downloading
"""

import json
import logging
import time
import argparse
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus, urljoin
from typing import Optional, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

# Paths
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
CAMPS_JSON = SCRIPT_DIR / "camps.json"
CANDIDATES_DIR = BASE_DIR / "images" / "candidates"
SCRAPER_DIR = BASE_DIR / "images" / "scraper"
DOWNLOAD_STATE_FILE = SCRAPER_DIR / "download_state.json"
LOG_FILE = SCRIPT_DIR / "gallery_scraper.log"

# Constants
GALLERY_BASE_URL = "https://gallery.burningman.org"
GALLERY_SEARCH_URL = f"{GALLERY_BASE_URL}/search/"
DEFAULT_MAX_IMAGES = 128
DEFAULT_CAMP_DELAY = 12  # seconds between camps
DEFAULT_PAGE_DELAY = 2.5  # seconds between search pages
DEFAULT_DETAIL_DELAY = 1.5  # seconds between asset detail fetches
DEFAULT_DOWNLOAD_DELAY = 1.5  # seconds between downloads

USER_AGENT = "BRC-Domesday-Scraper/1.0 (Research project; contact: joel@spolsky.com)"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_camps_data() -> List[Dict]:
    """Load the camps.json data."""
    logger.info(f"Loading camps data from {CAMPS_JSON}")
    with open(CAMPS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_download_state() -> Dict:
    """Load the download state file."""
    if not DOWNLOAD_STATE_FILE.exists():
        return {"camps": {}}

    try:
        with open(DOWNLOAD_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading download state: {e}")
        return {"camps": {}}


def save_download_state(state: Dict) -> None:
    """Save the download state file."""
    SCRAPER_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(DOWNLOAD_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving download state: {e}")


def update_download_state(camp_name: str, images_count: int) -> None:
    """Update download state for a camp."""
    state = load_download_state()

    if 'camps' not in state:
        state['camps'] = {}

    if camp_name not in state['camps']:
        state['camps'][camp_name] = {}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state['camps'][camp_name]['images_downloaded'] = images_count
    state['camps'][camp_name]['last_processed'] = timestamp
    state['camps'][camp_name]['status'] = 'success' if images_count > 0 else 'no_images_found'

    save_download_state(state)
    logger.debug(f"Updated download state for {camp_name}: {images_count} images")


def load_metadata(camp_name: str) -> Optional[Dict]:
    """Load existing metadata.json for a camp, if it exists."""
    camp_dir = CANDIDATES_DIR / camp_name
    metadata_file = camp_dir / "metadata.json"

    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading metadata for {camp_name}: {e}")
        return None


def save_metadata(camp_name: str, metadata: Dict) -> None:
    """Save metadata.json for a camp."""
    camp_dir = CANDIDATES_DIR / camp_name
    camp_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = camp_dir / "metadata.json"

    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.debug(f"Saved metadata for {camp_name}")


def get_next_image_number(metadata: Optional[Dict]) -> int:
    """Determine the next sequential image number for a camp."""
    if not metadata or 'images' not in metadata:
        return 1

    # Find highest existing image number
    max_num = 0
    for img in metadata['images']:
        filename = img.get('filename', '')
        match = re.match(r'image_(\d+)\.\w+$', filename)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    return max_num + 1


def get_existing_asset_ids(metadata: Optional[Dict]) -> set:
    """Extract set of already-downloaded asset IDs to avoid duplicates."""
    if not metadata or 'images' not in metadata:
        return set()

    asset_ids = set()
    for img in metadata['images']:
        if 'asset_id' in img:
            asset_ids.add(img['asset_id'])

    return asset_ids


def make_request(url: str, retries: int = 3, tolerate_404: bool = False) -> Optional[requests.Response]:
    """Make HTTP request with retries and exponential backoff."""
    headers = {'User-Agent': USER_AGENT}

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 429:  # Rate limited
                wait_time = 60
                logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            if response.status_code == 404 and tolerate_404:
                # 404 is expected for pagination beyond available pages
                return None

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            # If it's a 404 and we tolerate it, don't retry
            if tolerate_404 and "404" in str(e):
                return None

            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Request failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Request failed after {retries} attempts: {e}")
                return None

    return None


def search_gallery(camp_name: str, page_delay: float) -> List[Dict]:
    """
    Search gallery.burningman.org for a camp name.
    Returns list of image results with metadata.
    """
    logger.info(f"Searching gallery for: {camp_name}")

    query = quote_plus(camp_name)
    search_url = f"{GALLERY_SEARCH_URL}?q={query}"

    all_images = []
    page = 1

    while True:
        # Construct page URL
        if page == 1:
            url = search_url
            tolerate_404 = False  # First page should not 404
        else:
            url = f"{search_url}&p={page}"
            tolerate_404 = True  # Pagination beyond available pages will 404

        logger.debug(f"Fetching page {page}: {url}")
        response = make_request(url, tolerate_404=tolerate_404)

        if not response:
            if page > 1:
                # No more pages available
                logger.debug(f"No more pages available (page {page} returned 404)")
                break
            else:
                logger.warning(f"Failed to fetch page {page} for {camp_name}")
                break

        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for "no results" message
        if page == 1:
            no_results = soup.find(string=re.compile(r"No results for that search", re.IGNORECASE))
            if no_results:
                logger.info(f"No gallery results found for {camp_name}")
                return []

        # Extract images from this page
        page_images = extract_images_from_page(soup, search_url)

        if not page_images:
            logger.debug(f"No more images found on page {page}")
            break

        all_images.extend(page_images)
        logger.debug(f"Found {len(page_images)} images on page {page}")

        # Check if there are more pages
        # The gallery uses infinite scroll, but we can access pages via ?p= parameter
        # We'll stop when we get no results on a page
        page += 1

        # Rate limiting between pages
        if page_images:
            time.sleep(page_delay)

    logger.info(f"Found {len(all_images)} total images for {camp_name}")
    return all_images


def extract_images_from_page(soup: BeautifulSoup, search_url: str) -> List[Dict]:
    """Extract image metadata from a search results page."""
    images = []

    # Find all image result containers
    # Based on the HTML structure from our research, each result has:
    # - An <a> tag with href="/asset/[UUID]?..."
    # - An <img> tag with the thumbnail
    # - A photographer credit line

    # Look for links to asset pages
    asset_links = soup.find_all('a', href=re.compile(r'^/asset/[a-f0-9-]+'))

    for link in asset_links:
        href = link.get('href', '')

        # Extract asset ID from href
        match = re.search(r'/asset/([a-f0-9-]+)', href)
        if not match:
            continue

        asset_id = match.group(1)
        asset_url = urljoin(GALLERY_BASE_URL, f"/asset/{asset_id}")

        # Get thumbnail URL from img tag
        img_tag = link.find('img')
        if not img_tag:
            continue

        thumbnail_url = img_tag.get('src', '')
        if not thumbnail_url:
            continue

        # Get image title from the link text (usually in the next <a> tag)
        title = ""
        next_link = link.find_next_sibling('a')
        if next_link:
            title = next_link.get_text(strip=True)

        # Get photographer credit (usually appears after the title link)
        photographer = ""
        if next_link:
            next_text = next_link.find_next_sibling(string=True)
            if next_text:
                # Look for "Photo by: ..." pattern
                photo_by_match = re.search(r'Photo by:\s*(.+)', next_text, re.IGNORECASE)
                if photo_by_match:
                    photographer = photo_by_match.group(1).strip()

        images.append({
            'asset_id': asset_id,
            'asset_url': asset_url,
            'thumbnail_url': thumbnail_url,
            'title': title,
            'photographer': photographer,
            'search_url': search_url
        })

    return images


def fetch_asset_details(asset_id: str, asset_url: str, detail_delay: float) -> Dict:
    """Fetch additional metadata from asset detail page."""
    logger.debug(f"Fetching details for asset {asset_id}")

    response = make_request(asset_url)

    if not response:
        logger.warning(f"Failed to fetch asset details for {asset_id}")
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')

    details = {}

    # Get all text content to search for patterns
    page_text = soup.get_text()

    # Extract photographer - look for "Photo by: ..." pattern
    photo_by_match = re.search(r'Photo by:\s*(.+?)(?:\n|Year:|$)', page_text, re.IGNORECASE)
    if photo_by_match:
        photographer = photo_by_match.group(1).strip()
        if photographer:
            details['photographer'] = photographer
            logger.debug(f"Found photographer: {photographer}")

    # Extract year - look for "Year: YYYY" pattern
    year_match = re.search(r'Year:\s*(\d{4})', page_text)
    if year_match:
        year = int(year_match.group(1))
        details['year'] = year
        logger.debug(f"Found year: {year}")

    # Extract title from h1
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        if title:
            details['title'] = title
            logger.debug(f"Found title: {title}")

    # Extract caption from p tag (usually the first substantial paragraph)
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        text = p.get_text(strip=True)
        # Skip very short paragraphs (likely not captions)
        if len(text) > 50:
            details['caption'] = text
            logger.debug(f"Found caption: {text[:100]}...")
            break

    time.sleep(detail_delay)

    return details


def download_image(url: str, filepath: Path) -> Optional[Tuple[int, int, int]]:
    """
    Download image and return (width, height, size_bytes).
    Returns None if download fails.
    """
    try:
        response = make_request(url)
        if not response:
            return None

        # Save image
        with open(filepath, 'wb') as f:
            f.write(response.content)

        # Get dimensions
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        size_bytes = len(response.content)

        return (width, height, size_bytes)

    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        return None


def process_camp(
    camp_name: str,
    max_images: int,
    page_delay: float,
    detail_delay: float,
    download_delay: float,
    dry_run: bool
) -> Dict:
    """Process a single camp: search, download images, update metadata."""
    logger.info(f"Processing camp: {camp_name}")

    # Load existing metadata
    metadata = load_metadata(camp_name)
    if metadata is None:
        metadata = {
            "camp_name": camp_name,
            "images": []
        }

    # Get existing asset IDs to avoid duplicates
    existing_asset_ids = get_existing_asset_ids(metadata)

    # Get next image number
    next_img_num = get_next_image_number(metadata)

    # Count existing gallery images (images with asset_id)
    existing_gallery_count = sum(1 for img in metadata.get('images', []) if 'asset_id' in img)
    logger.info(f"Camp has {len(metadata.get('images', []))} total images, {existing_gallery_count} from gallery")

    # Search gallery
    search_results = search_gallery(camp_name, page_delay)

    if not search_results:
        logger.info(f"No gallery images found for {camp_name}")
        return {'camp_name': camp_name, 'images_added': 0, 'images_skipped': 0}

    # Process images
    images_added = 0
    images_skipped = 0

    for img_data in search_results:
        # Check if we've hit the limit for NEW gallery images
        if images_added >= max_images:
            logger.info(f"Reached limit of {max_images} NEW gallery images for {camp_name}")
            break

        asset_id = img_data['asset_id']

        # Skip if already downloaded
        if asset_id in existing_asset_ids:
            logger.debug(f"Skipping already-downloaded asset {asset_id}")
            images_skipped += 1
            continue

        # Fetch additional details from asset page
        details = fetch_asset_details(asset_id, img_data['asset_url'], detail_delay)

        # Prepare metadata entry
        filename = f"image_{next_img_num:05d}.jpg"
        download_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        image_metadata = {
            "filename": filename,
            "image_url": img_data['thumbnail_url'],
            "source_page_url": img_data['asset_url'],
            "original_url": img_data['asset_url'],
            "width": 300,  # Will be updated after download
            "height": 300,  # Will be updated after download
            "size_bytes": 0,  # Will be updated after download
            "download_date": download_date,
            "photographer": details.get('photographer', img_data.get('photographer', '')),
            "year": details.get('year'),
            "title": details.get('title', img_data.get('title', '')),
            "caption": details.get('caption', ''),
            "asset_id": asset_id
        }

        if not dry_run:
            # Download image
            camp_dir = CANDIDATES_DIR / camp_name
            camp_dir.mkdir(parents=True, exist_ok=True)
            filepath = camp_dir / filename

            result = download_image(img_data['thumbnail_url'], filepath)

            if result:
                width, height, size_bytes = result
                image_metadata['width'] = width
                image_metadata['height'] = height
                image_metadata['size_bytes'] = size_bytes

                # Add to metadata
                metadata['images'].append(image_metadata)
                images_added += 1
                next_img_num += 1

                logger.info(f"Downloaded {filename} for {camp_name}")

                time.sleep(download_delay)
            else:
                logger.warning(f"Failed to download image for asset {asset_id}")
                images_skipped += 1
        else:
            # Dry run - just log what we would do
            logger.info(f"[DRY RUN] Would download {filename} from {img_data['thumbnail_url']}")
            images_added += 1
            next_img_num += 1

    # Save updated metadata
    if not dry_run and images_added > 0:
        save_metadata(camp_name, metadata)

    # Update download state for curator
    if not dry_run:
        total_images = len(metadata['images'])
        update_download_state(camp_name, total_images)

    return {
        'camp_name': camp_name,
        'images_added': images_added,
        'images_skipped': images_skipped
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scrape images from gallery.burningman.org for Burning Man camps'
    )
    parser.add_argument('--camp', type=str, help='Process single camp only')
    parser.add_argument('--limit', type=int, help='Process only first N camps')
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip camps that already have gallery images')
    parser.add_argument('--max-images', type=int, default=DEFAULT_MAX_IMAGES,
                       help=f'Download max N images per camp (default: {DEFAULT_MAX_IMAGES})')
    parser.add_argument('--delay', type=float, default=DEFAULT_CAMP_DELAY,
                       help=f'Delay between camps in seconds (default: {DEFAULT_CAMP_DELAY})')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without downloading')

    args = parser.parse_args()

    # Print banner
    print("=" * 80)
    print("Burning Man Gallery Scraper")
    print("=" * 80)
    print()

    if args.dry_run:
        print("DRY RUN MODE - No files will be downloaded")
        print()

    # Load camps data
    camps_data = load_camps_data()
    logger.info(f"Loaded {len(camps_data)} camps")

    # Filter camps if needed
    if args.camp:
        camps_data = [c for c in camps_data if c.get('name') == args.camp]
        if not camps_data:
            logger.error(f"Camp '{args.camp}' not found in camps.json")
            return 1

    if args.limit:
        camps_data = camps_data[:args.limit]

    # Process camps
    total_camps = len(camps_data)
    results = []

    for idx, camp in enumerate(camps_data, 1):
        camp_name = camp.get('name')
        if not camp_name:
            logger.warning(f"Camp missing name, skipping")
            continue

        logger.info(f"Processing camp {idx} of {total_camps}: {camp_name}")

        # Skip if requested
        if args.skip_existing:
            metadata = load_metadata(camp_name)
            if metadata and metadata.get('images'):
                # Check if any images have asset_id (gallery images)
                has_gallery_images = any('asset_id' in img for img in metadata['images'])
                if has_gallery_images:
                    logger.info(f"Skipping {camp_name} - already has gallery images")
                    continue

        # Process camp
        result = process_camp(
            camp_name,
            args.max_images,
            DEFAULT_PAGE_DELAY,
            DEFAULT_DETAIL_DELAY,
            DEFAULT_DOWNLOAD_DELAY,
            args.dry_run
        )
        results.append(result)

        # Rate limiting between camps
        if idx < total_camps:
            logger.info(f"Waiting {args.delay} seconds before next camp...")
            time.sleep(args.delay)

    # Print summary
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)

    total_added = sum(r['images_added'] for r in results)
    total_skipped = sum(r['images_skipped'] for r in results)
    camps_with_images = sum(1 for r in results if r['images_added'] > 0)

    print(f"Camps processed: {len(results)}")
    print(f"Camps with new images: {camps_with_images}")
    print(f"Total images downloaded: {total_added}")
    print(f"Total images skipped: {total_skipped}")
    print()
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
