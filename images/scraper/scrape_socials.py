#!/usr/bin/env python3
"""
Social Media Image Scraper (Human-in-the-Loop)

A semi-automated tool for collecting camp images from social media platforms.
The script handles bookkeeping while a human operator manually downloads images.

Tip: Install "Downloader for Instagram" in Firefox to download images with one click.
    https://onlinetoolset.com/browser-extensions/downloader-for-instagram

Usage:
    python3 scrape_socials.py [OPTIONS]

Options:
    --start-camp CAMP_NAME    Start processing from this camp (skip all prior)
    --platform PLATFORM       Filter: 'instagram', 'facebook', 'all' (default: 'all')
    --downloads-dir PATH      Path to Downloads folder (default: ~/Downloads)
    --dry-run                 Show camps without launching browsers
    --list-camps              List all camps with social media URLs and exit
"""

import json
import os
import shutil
import webbrowser
import signal
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Set

from PIL import Image

# Paths relative to script location
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
CANDIDATES_DIR = BASE_DIR / "candidates"
DOWNLOAD_STATE_FILE = SCRIPT_DIR / "download_state.json"
CAMP_HISTORY_FILE = BASE_DIR.parent / "data" / "campHistory.json"

# Image file extensions to process
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic'}

# Global flag for graceful interruption
should_exit = False


def handle_interrupt(signum, frame):
    """Handle Ctrl+C gracefully."""
    global should_exit
    print("\n\nInterrupted! Will exit after current camp...")
    should_exit = True


signal.signal(signal.SIGINT, handle_interrupt)


def sanitize_filename(name: str) -> str:
    """Sanitize a camp name for use as a directory name."""
    # Replace problematic characters
    for char in '<>:"/\\|?*':
        name = name.replace(char, '-')
    return name


def get_image_dimensions(image_path: Path) -> Tuple[Optional[int], Optional[int]]:
    """Get width and height of an image file. Returns (width, height) or (None, None) on error."""
    try:
        with Image.open(image_path) as img:
            return img.size  # Returns (width, height)
    except Exception:
        return None, None


def is_instagram_url(url: str) -> bool:
    """Check if URL is an Instagram URL."""
    if not url:
        return False
    url_lower = url.lower()
    return 'instagram.com' in url_lower or 'instagr.am' in url_lower


def is_facebook_url(url: str) -> bool:
    """Check if URL is a Facebook URL."""
    if not url:
        return False
    url_lower = url.lower()
    return 'facebook.com' in url_lower or 'fb.com' in url_lower


def get_platform(url: str) -> Optional[str]:
    """Determine the social media platform from a URL."""
    if is_instagram_url(url):
        return 'instagram'
    elif is_facebook_url(url):
        return 'facebook'
    return None


def load_camp_history() -> Dict:
    """Load campHistory.json."""
    with open(CAMP_HISTORY_FILE, 'r') as f:
        return json.load(f)


def load_download_state() -> Dict:
    """Load download_state.json, creating if needed."""
    if DOWNLOAD_STATE_FILE.exists():
        with open(DOWNLOAD_STATE_FILE, 'r') as f:
            return json.load(f)
    return {"camps": {}}


def save_download_state(state: Dict):
    """Save download_state.json."""
    with open(DOWNLOAD_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_metadata(camp_name: str) -> Dict:
    """Load metadata.json for a camp, creating if needed."""
    camp_dir = CANDIDATES_DIR / sanitize_filename(camp_name)
    metadata_file = camp_dir / "metadata.json"

    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)

    return {
        "camp_name": camp_name,
        "images": []
    }


def save_metadata(camp_name: str, metadata: Dict):
    """Save metadata.json for a camp."""
    camp_dir = CANDIDATES_DIR / sanitize_filename(camp_name)
    camp_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = camp_dir / "metadata.json"

    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def get_camps_with_social_urls(camp_history: Dict, platform_filter: str) -> List[Tuple[str, str, str]]:
    """
    Extract camps with social media URLs.

    Returns list of (camp_name, platform, url) tuples.
    """
    results = []

    for camp_name, camp_data in sorted(camp_history.items()):
        history = camp_data.get('history', [])

        # Find most recent social media URL
        for entry in history:  # Already sorted by year descending
            url = entry.get('url', '')
            if not url:
                continue

            platform = get_platform(url)
            if platform:
                # Apply platform filter
                if platform_filter == 'all' or platform_filter == platform:
                    results.append((camp_name, platform, url))
                break  # Only use most recent URL per camp

    return results


def snapshot_downloads(downloads_dir: Path) -> Dict[str, Tuple[float, int]]:
    """
    Take a snapshot of the Downloads folder.

    Returns dict of filename -> (mtime, size).
    """
    snapshot = {}

    if not downloads_dir.exists():
        return snapshot

    for f in downloads_dir.iterdir():
        if f.is_file():
            try:
                stat = f.stat()
                snapshot[f.name] = (stat.st_mtime, stat.st_size)
            except OSError:
                pass  # File may have been deleted

    return snapshot


def find_new_images(downloads_dir: Path, old_snapshot: Dict[str, Tuple[float, int]]) -> List[Path]:
    """
    Find new image files in Downloads since the snapshot.

    Returns list of Path objects for new image files.
    """
    new_images = []

    for f in downloads_dir.iterdir():
        if not f.is_file():
            continue

        # Check if it's an image
        if f.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        try:
            stat = f.stat()

            # Skip empty files (still downloading)
            if stat.st_size == 0:
                continue

            # Check if new or modified
            old_info = old_snapshot.get(f.name)
            if old_info is None or stat.st_mtime > old_info[0]:
                new_images.append(f)

        except OSError:
            pass  # File may have been deleted

    return new_images


def process_images(
    camp_name: str,
    platform: str,
    source_url: str,
    new_images: List[Path],
    downloads_dir: Path
) -> int:
    """
    Move images to candidates folder and update metadata.

    Returns number of images processed.
    """
    if not new_images:
        return 0

    camp_dir = CANDIDATES_DIR / sanitize_filename(camp_name)
    camp_dir.mkdir(parents=True, exist_ok=True)

    metadata = load_metadata(camp_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processed = 0

    for img_path in new_images:
        original_filename = img_path.name

        # Generate new filename
        new_filename = f"{platform}_{timestamp}_{original_filename}"
        dest_path = camp_dir / new_filename

        # Handle collision
        counter = 1
        while dest_path.exists():
            base, ext = os.path.splitext(new_filename)
            new_filename = f"{base}_{counter}{ext}"
            dest_path = camp_dir / new_filename
            counter += 1

        try:
            # Get dimensions before moving
            width, height = get_image_dimensions(img_path)

            # Move the file
            shutil.move(str(img_path), str(dest_path))
            print(f"  Moved: {original_filename} -> {new_filename}", end="")
            if width and height:
                print(f" ({width}x{height})")
            else:
                print()

            # Add to metadata
            image_entry = {
                "filename": new_filename,
                "source_page_url": source_url,
                "original_filename": original_filename,
                "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": platform
            }
            if width and height:
                image_entry["width"] = width
                image_entry["height"] = height

            metadata['images'].append(image_entry)

            processed += 1

        except Exception as e:
            print(f"  Error moving {original_filename}: {e}")

    # Save metadata
    save_metadata(camp_name, metadata)

    return processed


def update_download_state(
    camp_name: str,
    platform: str,
    source_url: str,
    images_count: int
):
    """Update download_state.json for this camp."""
    state = load_download_state()

    if camp_name not in state['camps']:
        state['camps'][camp_name] = {
            "urls_provided": [],
            "urls_checked": [],
            "social_media_urls": [],
            "error_urls": [],
            "redirected_urls": {},
            "images_downloaded": 0,
            "status": "success"
        }

    camp_state = state['camps'][camp_name]

    # Add URL to lists if not present
    if source_url not in camp_state['urls_provided']:
        camp_state['urls_provided'].append(source_url)
    if source_url not in camp_state['urls_checked']:
        camp_state['urls_checked'].append(source_url)
    if source_url not in camp_state['social_media_urls']:
        camp_state['social_media_urls'].append(source_url)

    # Update counts and timestamp
    camp_state['images_downloaded'] = camp_state.get('images_downloaded', 0) + images_count
    camp_state['last_processed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    camp_state['status'] = "success"

    save_download_state(state)


def print_header(camp_name: str, index: int, total: int, platform: str, url: str):
    """Print the header for a camp."""
    print()
    print("=" * 70)
    print(f"Processing: {camp_name} ({index} of {total} with {platform.title()})")
    print(f"URL: {url}")
    print("=" * 70)
    print("Instructions:")
    print("  - Browse the page and download any relevant camp images")
    print("  - Press Enter here when done (or Ctrl+C to stop)")
    print(f"  - Images will be moved to: images/candidates/{sanitize_filename(camp_name)}/")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Semi-automated social media image scraper"
    )
    parser.add_argument(
        '--start-camp',
        help="Start processing from this camp (skip all prior)"
    )
    parser.add_argument(
        '--platform',
        choices=['instagram', 'facebook', 'all'],
        default='all',
        help="Filter to specific platform (default: all)"
    )
    parser.add_argument(
        '--downloads-dir',
        type=Path,
        default=Path.home() / "Downloads",
        help="Path to Downloads folder (default: ~/Downloads)"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show camps without launching browsers"
    )
    parser.add_argument(
        '--list-camps',
        action='store_true',
        help="List all camps with social media URLs and exit"
    )

    args = parser.parse_args()

    # Validate downloads directory
    if not args.downloads_dir.exists():
        print(f"Error: Downloads directory not found: {args.downloads_dir}")
        print("Use --downloads-dir to specify the correct path")
        sys.exit(1)

    # Load camp data
    print("Loading camp data...")
    try:
        camp_history = load_camp_history()
    except FileNotFoundError:
        print(f"Error: campHistory.json not found at {CAMP_HISTORY_FILE}")
        print("Make sure you're running from the correct directory")
        sys.exit(1)

    # Get camps with social media URLs
    camps = get_camps_with_social_urls(camp_history, args.platform)

    if not camps:
        print(f"No camps found with {args.platform} URLs")
        sys.exit(0)

    # Handle --list-camps
    if args.list_camps:
        print(f"\nCamps with {args.platform} URLs ({len(camps)} total):\n")
        for camp_name, platform, url in camps:
            print(f"  [{platform:10}] {camp_name}")
            print(f"              {url}")
        sys.exit(0)

    # Apply --start-camp filter
    start_index = 0
    if args.start_camp:
        found = False
        for i, (camp_name, _, _) in enumerate(camps):
            if camp_name == args.start_camp:
                start_index = i
                found = True
                break

        if not found:
            print(f"Error: Camp '{args.start_camp}' not found in social media list")
            print("Use --list-camps to see available camps")
            sys.exit(1)

    camps = camps[start_index:]
    total_camps = len(camps)

    platform_label = args.platform.title() if args.platform != 'all' else 'social media'
    print(f"Found {total_camps} camps with {platform_label} URLs")

    if args.dry_run:
        print("\n[DRY RUN] Would process these camps:\n")
        for i, (camp_name, platform, url) in enumerate(camps, 1):
            print(f"  {i}. [{platform}] {camp_name}")
            print(f"     {url}")
        sys.exit(0)

    # Take initial snapshot of Downloads
    downloads_snapshot = snapshot_downloads(args.downloads_dir)

    # Track statistics
    total_images = 0
    camps_processed = 0
    images_by_platform = {}
    last_camp = None

    # Main processing loop
    for i, (camp_name, platform, url) in enumerate(camps, 1):
        if should_exit:
            break

        last_camp = camp_name
        print_header(camp_name, start_index + i, start_index + total_camps, platform, url)

        # Launch browser
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"  Warning: Could not launch browser: {e}")
            print("  Please open the URL manually")

        # Wait for user
        try:
            input("Press Enter when done with this camp (or Ctrl+C to stop)... ")
        except EOFError:
            # Handle piped input or closed stdin
            break

        if should_exit:
            break

        # Find new images
        new_images = find_new_images(args.downloads_dir, downloads_snapshot)

        # Process images
        if new_images:
            count = process_images(camp_name, platform, url, new_images, args.downloads_dir)
            total_images += count
            images_by_platform[platform] = images_by_platform.get(platform, 0) + count

            # Update download state
            update_download_state(camp_name, platform, url, count)

            print(f"  Processed {count} new image(s) for {camp_name}")
        else:
            print("  No new images found")
            # Still update download state to mark as checked
            update_download_state(camp_name, platform, url, 0)

        # Update snapshot for next iteration
        downloads_snapshot = snapshot_downloads(args.downloads_dir)
        camps_processed += 1

        # Show next camp preview
        if i < total_camps and not should_exit:
            next_camp = camps[i][0]
            print(f"  Next: {next_camp} ({start_index + i + 1} of {start_index + total_camps})")

    # Print summary
    print()
    print("=" * 70)
    if should_exit:
        print("Session Paused")
    else:
        print("Session Complete")
    print("=" * 70)
    print(f"Camps processed: {camps_processed} of {total_camps}")
    print(f"Total images collected: {total_images}")

    if images_by_platform:
        print("Images by platform:")
        for platform, count in sorted(images_by_platform.items()):
            print(f"  {platform.title()}: {count}")

    # Show resume command if interrupted mid-way
    if should_exit and last_camp and camps_processed < total_camps:
        # Find next camp
        next_index = camps_processed
        if next_index < len(camps):
            next_camp = camps[next_index][0]
            print()
            print("To resume, use:")
            print(f'  python3 {sys.argv[0]} --start-camp "{next_camp}"')

    print()
    print("Next step: Run the curator to review candidates")
    print("  cd ../curator && python3 curator_server.py")
    print("=" * 70)


if __name__ == '__main__':
    main()
