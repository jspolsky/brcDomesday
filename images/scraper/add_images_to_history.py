#!/usr/bin/env python3
"""
Add Approved Images to Camp History

This script reads the curation results from the candidates directory,
processes images from gallery.burningman.org to create thumbnails,
uploads them to S3, and adds the approved images to campHistory.json.

For images from gallery.burningman.org:
- Downloads the full-size image
- Resizes to max 1024px width (maintaining aspect ratio)
- Uploads to S3 bucket (brcdomesday-thumbnails)
- Caches thumbnail URLs in metadata.json to avoid reprocessing

Usage:
    python3 add_images_to_history.py [--verbose] [--max-thumbnails N]

Options:
    --verbose           Print detailed debug information
    --max-thumbnails N  Process only N thumbnails (for testing)

The script is idempotent - running it multiple times will use cached
thumbnails and only process new images.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urljoin
from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup
from PIL import Image
import boto3

# Paths
IMAGES_DIR = Path(__file__).parent.parent
CANDIDATES_DIR = IMAGES_DIR / "candidates"
DATA_DIR = IMAGES_DIR.parent / "data"
TMP_DIR = IMAGES_DIR.parent / "tmp"
CAMP_HISTORY_FILE = DATA_DIR / "campHistory.json"

# S3 Configuration
S3_BUCKET_NAME = "brcdomesday-thumbnails"

def create_thumbnail(image_data, verbose=False, thumbnails_remaining=None):
    """
    Create a thumbnail for an image from gallery.burningman.org.

    Process:
    1. Checks if source_page_url is from gallery.burningman.org (skips if not)
    2. Fetches the gallery page HTML and finds the full-size image
    3. Downloads the full-size image
    4. Resizes to max 1024px width using LANCZOS algorithm (maintains aspect ratio)
    5. Uploads to S3 bucket (brcdomesday-thumbnails)
    6. Updates image_data with S3 URL and new dimensions
    7. Pauses 10 seconds to be polite to the gallery server

    Args:
        image_data: Dictionary containing url, width, height, source_page_url,
                   and optionally photographer and year
        verbose: If True, print detailed debug information
        thumbnails_remaining: List with one element tracking remaining thumbnail count
                             (decremented when a thumbnail is processed)

    Returns:
        Modified image_data dictionary with S3 URL and updated dimensions,
        or unchanged if not a gallery image or on error
    """
    # Only process images from gallery.burningman.org
    source_url = image_data.get('source_page_url', '')
    if not source_url.startswith('https://gallery.burningman.org'):
        # Not a gallery image, return unchanged
        return image_data

    if verbose:
        print(f"\n  create_thumbnail INPUT:")
        print(f"    {json.dumps(image_data, indent=6)}")

    try:
        # Step 1: Fetch the HTML from the gallery page
        if verbose:
            print(f"  Fetching HTML from: {source_url}")

        response = requests.get(source_url, timeout=30)
        response.raise_for_status()

        # Step 2: Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Step 3: Find the <img> tag with id="bigImg"
        big_img = soup.find('img', id='bigImg')
        if not big_img:
            if verbose:
                print(f"  WARNING: Could not find img tag with id='bigImg'")
            return image_data

        # Step 4: Get the image source URL
        img_src = big_img.get('data-src')
        if not img_src:
            if verbose:
                print(f"  WARNING: img tag has no data-src attribute")
            return image_data

        # Make the URL absolute if it's relative
        img_url = urljoin(source_url, img_src)

        if verbose:
            print(f"  Found image URL: {img_url}")

        # Step 5: Download the image to a temporary file
        if verbose:
            print(f"  Downloading image...")

        img_response = requests.get(img_url, timeout=30)
        img_response.raise_for_status()

        # Determine file extension from Content-Type header
        content_type = img_response.headers.get('Content-Type', '').lower()

        # Map common image MIME types to extensions
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
        }

        # Try to get extension from Content-Type, fall back to URL, then default to .jpg
        img_ext = mime_to_ext.get(content_type.split(';')[0].strip())
        if not img_ext:
            img_ext = os.path.splitext(img_url)[1] or '.jpg'

        if verbose:
            print(f"  Content-Type: {content_type}, using extension: {img_ext}")

        # Create tmp directory if it doesn't exist
        TMP_DIR.mkdir(exist_ok=True)

        # Create a unique filename using timestamp
        import time
        timestamp = str(int(time.time() * 1000000))  # microseconds for uniqueness
        temp_filename = f"thumbnail_{timestamp}{img_ext}"
        temp_filepath = TMP_DIR / temp_filename

        # Write the downloaded image
        with open(temp_filepath, 'wb') as f:
            f.write(img_response.content)

        if verbose:
            print(f"  Downloaded to: {temp_filepath}")

        # Step 6: Scale the image down if width > 1024
        img = Image.open(temp_filepath)
        original_width, original_height = img.size

        if verbose:
            print(f"  Original dimensions: {original_width} × {original_height}")

        if original_width > 1024:
            # Calculate new dimensions maintaining aspect ratio
            new_width = 1024
            new_height = int((original_height * new_width) / original_width)

            if verbose:
                print(f"  Resizing to: {new_width} × {new_height}")

            # Resize using LANCZOS for best quality when downscaling
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)

            # Save the resized image back to the temp file
            resized_img.save(temp_filepath)

            # Update dimensions in output_data
            output_data = image_data.copy()
            output_data['width'] = new_width
            output_data['height'] = new_height

            if verbose:
                print(f"  Saved resized image")
        else:
            if verbose:
                print(f"  No resize needed (width <= 1024)")
            output_data = image_data

        # Close the image
        img.close()

        # Step 7: Upload to S3
        if verbose:
            print(f"  Uploading to S3 bucket: {S3_BUCKET_NAME}")

        load_dotenv()
        s3_client = boto3.client('s3')
        s3_key = temp_filename  # Use the same filename in S3

        # Determine content type for S3
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
        }
        s3_content_type = content_type_map.get(img_ext, 'image/jpeg')

        # Upload to S3
        s3_client.upload_file(
            str(temp_filepath),
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': s3_content_type
            }
        )

        # Generate S3 URL
        s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        if verbose:
            print(f"  Uploaded to: {s3_url}")

        # Update the image_data with the S3 URL
        output_data['url'] = s3_url

        # Delete the temporary file
        os.unlink(temp_filepath)
        if verbose:
            print(f"  Deleted temporary file")

        # Pause to avoid hammering the gallery server
        if verbose:
            print(f"  Pausing 10 seconds to be polite to gallery.burningman.org...")
        time.sleep(10)

    except Exception as e:
        if verbose:
            print(f"  ERROR creating thumbnail: {e}")
        # Return original data on error
        output_data = image_data

    # Decrement the thumbnail counter (only for processed thumbnails)
    if thumbnails_remaining and thumbnails_remaining[0] is not None:
        thumbnails_remaining[0] -= 1

    if verbose:
        print(f"  create_thumbnail OUTPUT:")
        print(f"    {json.dumps(output_data, indent=6)}")

    return output_data

def upload_local_image(camp_name, image_data, verbose=False):
    """
    Upload a local image (from social media) to S3.

    Process:
    1. Reads the local image file from candidates directory
    2. Resizes to max 1024px width using LANCZOS algorithm (maintains aspect ratio)
    3. Uploads to S3 bucket (brcdomesday-thumbnails)
    4. Updates image_data with S3 URL and new dimensions

    Args:
        camp_name: Name of the camp (used to find the candidates directory)
        image_data: Dictionary containing filename, width, height, source_page_url
        verbose: If True, print detailed debug information

    Returns:
        Modified image_data dictionary with S3 URL and updated dimensions,
        or None on error
    """
    import time

    filename = image_data.get('filename')
    if not filename:
        if verbose:
            print(f"  ERROR: No filename in image_data")
        return None

    # Find the local file
    camp_dir = CANDIDATES_DIR / camp_name
    local_filepath = camp_dir / filename

    if not local_filepath.exists():
        if verbose:
            print(f"  ERROR: Local file not found: {local_filepath}")
        return None

    if verbose:
        print(f"\n  upload_local_image INPUT:")
        print(f"    {json.dumps(image_data, indent=6)}")
        print(f"  Reading local file: {local_filepath}")

    try:
        # Get file extension
        img_ext = os.path.splitext(filename)[1].lower() or '.jpg'

        # Create tmp directory if it doesn't exist
        TMP_DIR.mkdir(exist_ok=True)

        # Create a unique filename using timestamp
        timestamp = str(int(time.time() * 1000000))  # microseconds for uniqueness
        temp_filename = f"social_{timestamp}{img_ext}"
        temp_filepath = TMP_DIR / temp_filename

        # Open and process the image
        img = Image.open(local_filepath)
        original_width, original_height = img.size

        if verbose:
            print(f"  Original dimensions: {original_width} x {original_height}")

        output_data = image_data.copy()

        if original_width > 1024:
            # Calculate new dimensions maintaining aspect ratio
            new_width = 1024
            new_height = int((original_height * new_width) / original_width)

            if verbose:
                print(f"  Resizing to: {new_width} x {new_height}")

            # Resize using LANCZOS for best quality when downscaling
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            resized_img.save(temp_filepath)
            resized_img.close()

            output_data['width'] = new_width
            output_data['height'] = new_height
        else:
            # No resize needed, just copy the file
            if verbose:
                print(f"  No resize needed (width <= 1024)")
            img.save(temp_filepath)
            output_data['width'] = original_width
            output_data['height'] = original_height

        img.close()

        # Upload to S3
        if verbose:
            print(f"  Uploading to S3 bucket: {S3_BUCKET_NAME}")

        load_dotenv()
        s3_client = boto3.client('s3')
        s3_key = temp_filename

        # Determine content type for S3
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.heic': 'image/heic',
        }
        s3_content_type = content_type_map.get(img_ext, 'image/jpeg')

        # Upload to S3
        s3_client.upload_file(
            str(temp_filepath),
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': s3_content_type
            }
        )

        # Generate S3 URL
        s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        if verbose:
            print(f"  Uploaded to: {s3_url}")

        # Update the output data with the S3 URL
        output_data['url'] = s3_url

        # Delete the temporary file
        os.unlink(temp_filepath)
        if verbose:
            print(f"  Deleted temporary file")

        if verbose:
            print(f"  upload_local_image OUTPUT:")
            print(f"    {json.dumps(output_data, indent=6)}")

        return output_data

    except Exception as e:
        if verbose:
            print(f"  ERROR uploading local image: {e}")
        return None


def load_camp_history():
    """Load the campHistory.json file."""
    with open(CAMP_HISTORY_FILE, 'r') as f:
        return json.load(f)

def save_camp_history(history):
    """Save the campHistory.json file."""
    with open(CAMP_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def save_thumbnail_to_metadata(camp_name, image_filename, thumbnail_url, thumbnail_width, thumbnail_height):
    """
    Save thumbnail information back to the metadata.json file.

    This caches the thumbnail data to avoid regenerating thumbnails on
    subsequent runs. Adds three fields to the image entry: thumbnail_url,
    thumbnail_width, and thumbnail_height.

    Args:
        camp_name: Name of the camp
        image_filename: Filename of the image in metadata
        thumbnail_url: S3 URL of the uploaded thumbnail
        thumbnail_width: Width of the resized thumbnail
        thumbnail_height: Height of the resized thumbnail
    """
    camp_dir = CANDIDATES_DIR / camp_name
    metadata_file = camp_dir / "metadata.json"

    # Read the metadata
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    # Find and update the image
    for img in metadata.get('images', []):
        if img.get('filename') == image_filename:
            img['thumbnail_url'] = thumbnail_url
            img['thumbnail_width'] = thumbnail_width
            img['thumbnail_height'] = thumbnail_height
            break

    # Write back to file
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

def get_approved_images_for_camp(camp_name, verbose=False, thumbnails_remaining=None):
    """
    Get all approved images for a camp from its metadata.json file.

    For each approved image:
    - Checks if a thumbnail already exists in metadata (thumbnail_url field)
    - If yes, uses the cached thumbnail URL and dimensions
    - If no, calls create_thumbnail to generate and upload one
    - Saves newly created thumbnail info back to metadata.json

    Args:
        camp_name: Name of the camp
        verbose: If True, print debug information
        thumbnails_remaining: List with one element tracking remaining thumbnail count

    Returns:
        List of image dictionaries with url, width, height, source_page_url,
        and optionally photographer and year. For gallery images, url points to
        S3 thumbnail and dimensions reflect the resized image.
    """
    if verbose:
        print(f"👉  {camp_name}")

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
            # Check if thumbnail already exists
            # Get the image URL - gallery images have 'image_url', social media images don't
            image_url = img.get('image_url')
            source_page_url = img.get('source_page_url', image_url)

            if img.get('thumbnail_url'):
                # Use existing thumbnail
                if verbose:
                    print(f"  Using existing thumbnail for {img.get('filename')}")
                image_data = {
                    'url': img['thumbnail_url'],
                    'width': img['thumbnail_width'],
                    'height': img['thumbnail_height'],
                    'source_page_url': source_page_url
                }
            elif image_url:
                # Check if this is a gallery image or a website-scraped image
                is_gallery = source_page_url and source_page_url.startswith('https://gallery.burningman.org')

                if is_gallery:
                    # Gallery image - need to create thumbnail
                    image_data = {
                        'url': image_url,
                        'width': img.get('width'),
                        'height': img.get('height'),
                        'source_page_url': source_page_url
                    }

                    # Store original image data for comparison
                    original_url = image_data['url']

                    # Create thumbnail
                    image_data = create_thumbnail(image_data, verbose=verbose,
                                                 thumbnails_remaining=thumbnails_remaining)

                    # If thumbnail was created (URL changed), save it to metadata
                    if image_data['url'] != original_url:
                        save_thumbnail_to_metadata(
                            camp_name,
                            img['filename'],
                            image_data['url'],
                            image_data['width'],
                            image_data['height']
                        )
                        if verbose:
                            print(f"  Saved thumbnail info to metadata.json")
                else:
                    # Website-scraped image - upload local copy to S3
                    local_image_data = {
                        'filename': img.get('filename'),
                        'width': img.get('width'),
                        'height': img.get('height'),
                        'source_page_url': source_page_url
                    }
                    image_data = upload_local_image(camp_name, local_image_data, verbose=verbose)

                    if image_data is None:
                        if verbose:
                            print(f"  Failed to upload {img.get('filename')}, skipping")
                        continue

                    # Decrement the thumbnail counter
                    if thumbnails_remaining and thumbnails_remaining[0] is not None:
                        thumbnails_remaining[0] -= 1

                    # Save thumbnail info to metadata for caching
                    save_thumbnail_to_metadata(
                        camp_name,
                        img['filename'],
                        image_data['url'],
                        image_data['width'],
                        image_data['height']
                    )
                    if verbose:
                        print(f"  Saved thumbnail info to metadata.json")
            else:
                # Social media image - local file, upload to S3
                local_image_data = {
                    'filename': img.get('filename'),
                    'width': img.get('width'),
                    'height': img.get('height'),
                    'source_page_url': source_page_url
                }
                image_data = upload_local_image(camp_name, local_image_data, verbose=verbose)

                if image_data is None:
                    if verbose:
                        print(f"  Failed to upload {img.get('filename')}, skipping")
                    continue

                # Decrement the thumbnail counter
                if thumbnails_remaining and thumbnails_remaining[0] is not None:
                    thumbnails_remaining[0] -= 1

                # Save thumbnail info to metadata for caching
                save_thumbnail_to_metadata(
                    camp_name,
                    img['filename'],
                    image_data['url'],
                    image_data['width'],
                    image_data['height']
                )
                if verbose:
                    print(f"  Saved thumbnail info to metadata.json")

            # Add photographer if available
            if img.get('photographer'):
                image_data['photographer'] = img['photographer']

            # Add year if available
            if img.get('year'):
                image_data['year'] = img['year']

            approved_images.append(image_data)

            # Check if we've hit the limit and should stop processing more images
            if thumbnails_remaining and thumbnails_remaining[0] is not None and thumbnails_remaining[0] <= 0:
                break

    return approved_images

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Process approved images from gallery.burningman.org, create thumbnails, upload to S3, and add to campHistory.json'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed debug information (download progress, resize details, S3 uploads)'
    )
    parser.add_argument(
        '--max-thumbnails',
        type=int,
        default=None,
        help='Process only N gallery thumbnails then exit (for testing/debugging)'
    )
    args = parser.parse_args()

    print("=" * 80)
    print("Adding Approved Images to Camp History")
    print("=" * 80)
    print()

    if args.verbose:
        print("Verbose mode enabled - will print thumbnail creation details")
        print()

    if args.max_thumbnails:
        print(f"Max thumbnails mode: will process only {args.max_thumbnails} thumbnail(s)")
        print()

    # Create mutable counter for max_thumbnails (list with one element)
    thumbnails_remaining = [args.max_thumbnails] if args.max_thumbnails else [None]

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
        approved_images = get_approved_images_for_camp(camp_name, verbose=args.verbose,
                                                       thumbnails_remaining=thumbnails_remaining)

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

        # Check if we've reached the max thumbnail limit
        if thumbnails_remaining[0] is not None and thumbnails_remaining[0] <= 0:
            print(f"\n  Reached max thumbnail limit, stopping early")
            break

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
