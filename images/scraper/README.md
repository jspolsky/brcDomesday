# Image Scraper

This script downloads candidate images from camp websites.

## Setup

Install dependencies:

```bash
pip3 install -r requirements.txt
```

## Usage

Run the scraper:

```bash
python3 scrape_images.py
```

The script will:
- Load camp data from `campHistory.json`
- Process each camp's website URLs
- Download images that appear to be camp photos
- Save images to `../candidates/[camp_name]/`
- Track progress in `download_state.json`

## Features

- **Resumable**: Press Ctrl+C to stop, run again to resume
- **Rate limiting**: 2 second delay between requests
- **Smart filtering**: Skips small images (< 100px) and non-photos
- **Social media handling**: Tracks Facebook/Instagram URLs separately
- **Metadata tracking**: Records source URLs, image dimensions, download dates

## Output

For each camp:
- `../candidates/[camp_name]/image_00001.jpg` - Downloaded images
- `../candidates/[camp_name]/metadata.json` - Image metadata

Global files:
- `download_state.json` - Which camps have been processed
- `social_media_camps.json` - Camps with Facebook/Instagram URLs

## Limits

- Maximum 128 images per camp
- Minimum 100x100 pixels per image
- Only downloads PNG and JPEG (no GIFs, videos, or animations)
