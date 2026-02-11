# Image Scraper & Processing Pipeline

This directory contains scripts for downloading, curating, and hosting camp images.

## Setup

Install dependencies:

```bash
pip3 install -r requirements.txt
```

Requires AWS credentials configured for S3 access (used by `add_images_to_history.py`). Create a `.env` file with your AWS credentials or configure via `~/.aws/credentials`.

## Pipeline Overview

The image pipeline has four stages:

1. **Scraping** - Download candidate images from camp websites, gallery.burningman.org, and social media
2. **Curation** - Human review to approve/reject candidates via web UI
3. **Processing** - Resize approved images and upload to S3
4. **Integration** - Add S3-hosted image URLs to `campHistory.json`

## Scripts

### 1. scrape_images.py - Website Scraper

Downloads candidate images from camp websites.

```bash
python3 scrape_images.py
```

- Loads camp data from `campHistory.json`
- Crawls each camp's website URLs (up to 50 pages, 3 levels deep)
- Downloads images that appear to be camp photos
- Saves to `../candidates/[camp_name]/`
- **Parallel processing**: Up to 16 camps simultaneously
- **Resumable**: Tracks progress in `download_state.json`
- **Smart filtering**: Skips small images (< 256x256px) and non-photos
- Maximum 128 images per camp

### 2. scrape_gallery.py - Burning Man Gallery Scraper

Downloads candidate images from gallery.burningman.org. See `borg-gallery-spec.md` for design details.

### 3. scrape_socials.py - Social Media Collector

Semi-automated tool for collecting images from Instagram/Facebook. Opens browser tabs for human to download images, then moves them into the candidates directory. See `scrape_socials_spec.md` for design details.

### 4. curator_server.py - Curation Web UI

Web-based interface for approving/rejecting candidate images. Sets `curation_result` field in each camp's `metadata.json`.

### 5. add_images_to_history.py - S3 Upload & Integration

Processes all approved images and adds them to `campHistory.json`:

```bash
python3 add_images_to_history.py [--verbose] [--max-thumbnails N]
```

For each approved image in `metadata.json`:
- **Gallery images** (from gallery.burningman.org): Downloads full-size image from gallery page, resizes to max 1024px width, uploads to S3
- **Website-scraped and social media images**: Reads local file from candidates directory, resizes to max 1024px width, uploads to S3
- **Cached images**: If `thumbnail_url` exists in metadata, uses cached S3 URL (skips upload)

All images end up hosted on S3 (`https://brcdomesday-thumbnails.s3.amazonaws.com/...`) to avoid broken links from camp websites going down or blocking hotlinking.

The script is **idempotent** - it caches S3 URLs in `metadata.json` (`thumbnail_url` field) and skips already-uploaded images on re-runs.

## Output

For each camp:
- `../candidates/[camp_name]/image_00001.jpg` - Downloaded images
- `../candidates/[camp_name]/metadata.json` - Image metadata (includes curation results and cached S3 URLs)

Global files:
- `download_state.json` - Which camps have been processed by scrapers
- `social_media_camps.json` - Camps with Facebook/Instagram URLs

Final output:
- `data/campHistory.json` - Updated with `images` arrays containing S3-hosted URLs

## Limits

- Maximum 128 candidate images per camp
- Minimum 256x256 pixels per image (both width AND height)
- Only downloads PNG and JPEG (no GIFs, videos, or animations)
- Thumbnails resized to max 1024px width (aspect ratio preserved)
