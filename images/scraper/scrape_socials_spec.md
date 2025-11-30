# Detailed Specification: scrape_socials.py

## Overview

`scrape_socials.py` is a semi-automated tool for collecting camp images from social media platforms. Unlike fully automated scrapers, this tool works cooperatively with a human operator who manually downloads images from social media pages, while the script handles bookkeeping, file management, and integration with the existing curation pipeline.

## Design Philosophy

Social media platforms actively prevent automated scraping. Rather than fighting this with complex browser automation that breaks frequently, we embrace a human-in-the-loop approach:
- The script handles all the tedious bookkeeping
- The human handles the visual judgment (is this image relevant to the camp?) and the actual downloading
- This produces higher quality candidates since a human is pre-filtering

## Command Line Interface

```bash
python3 scrape_socials.py [OPTIONS]

Options:
  --start-camp CAMP_NAME    Start processing from this camp (skip all prior camps)
  --platform PLATFORM       Filter to specific platform: 'instagram', 'facebook', 'all' (default: 'all')
  --downloads-dir PATH      Path to Downloads folder (default: ~/Downloads)
  --dry-run                 Show which camps would be processed without launching browsers
  --list-camps              List all camps with social media URLs and exit
```

## Data Flow

```
campHistory.json
       │
       ▼
┌──────────────────┐
│ Filter camps     │
│ with social URLs │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────┐
│ Launch browser   │────▶│ User views page │
│ tab to URL       │     │ & downloads     │
└──────────────────┘     └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ ~/Downloads     │
                         │ (new images)    │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────────────────┐
                         │ Move to candidates folder   │
                         │ images/candidates/[camp]/   │
                         └────────┬────────────────────┘
                                  │
                                  ▼
                         ┌─────────────────────────────┐
                         │ Update metadata.json        │
                         │ (source: instagram, etc.)   │
                         └─────────────────────────────┘
```

## Detailed Algorithm

### Phase 1: Initialization

1. **Parse command line arguments**
   - Validate `--start-camp` exists in the dataset if provided
   - Validate `--downloads-dir` exists and is readable
   - Validate `--platform` is one of: 'instagram', 'facebook', 'all'

2. **Load campHistory.json**
   - Parse the JSON file from `data/campHistory.json`

3. **Build list of camps with social media URLs**
   - For each camp in campHistory.json:
     - Check all history entries for URLs matching social media patterns
     - Instagram: `instagram.com` in URL
     - Facebook: `facebook.com` in URL (future)
     - Use the most recent (highest year) URL if multiple exist
   - Filter by `--platform` if specified
   - Store as list of tuples: `(camp_name, platform, url)`

4. **Apply --start-camp filter**
   - If `--start-camp` provided, find its index in the list
   - If not found, exit with error: "Camp 'X' not found in social media list. Use --list-camps to see available camps."
   - Slice list to start from that camp

5. **Snapshot the Downloads folder**
   - Record all current files in `--downloads-dir`
   - Store as set of `(filename, mtime, size)` tuples for reliable detection of new files

### Phase 2: Main Processing Loop

For each `(camp_name, platform, url)` in the filtered list:

#### Step 2.1: Display Progress
```
══════════════════════════════════════════════════════════════════
Processing: Camp Bird of Paradise (1 of 47 with Instagram)
URL: https://www.instagram.com/campbirdofparadise
══════════════════════════════════════════════════════════════════
Instructions:
  • Browse the page and download any relevant camp images
  • Close the browser tab when done (or press Enter here to continue)
  • Downloaded images will be moved to: images/candidates/Camp Bird of Paradise/
```

#### Step 2.2: Launch Browser Tab
- Use `webbrowser.open(url)` to open the URL in the user's default browser
- This opens a new tab, not a new window (browser-dependent but usually works)

#### Step 2.3: Wait for User Completion
- Primary method: Wait for user to press Enter in the terminal
- Display: `Press Enter when done with this camp (or Ctrl+C to stop)...`
- The "close tab detection" mentioned in requirements is not reliably possible without browser extensions, so we use Enter key instead

#### Step 2.4: Detect New Downloads
- Re-scan the Downloads folder
- Compare against the snapshot from Phase 1 (or previous iteration)
- New files are those that:
  - Were not in the previous snapshot, OR
  - Have a newer mtime than when we last checked
- Filter to image files only: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` (case-insensitive)
- Ignore files still being written (size = 0 or file locked)

#### Step 2.5: Process New Images
For each new image file found:

1. **Sanitize camp name for filesystem**
   - Replace `/` with `-`
   - Replace other problematic characters: `<>:"\|?*`
   - Preserve Unicode characters (camp names may have non-ASCII)

2. **Ensure candidate directory exists**
   ```
   images/candidates/{sanitized_camp_name}/
   ```

3. **Generate unique filename**
   - Format: `{platform}_{timestamp}_{original_filename}`
   - Example: `instagram_20250129_143052_photo1.jpg`
   - If filename collision, append `_1`, `_2`, etc.

4. **Move file from Downloads to candidates folder**
   - Use `shutil.move()` for atomic operation
   - Print: `  Moved: photo1.jpg → images/candidates/Camp Name/instagram_20250129_143052_photo1.jpg`

5. **Update metadata.json**
   - Load existing `images/candidates/{camp_name}/metadata.json` or create new
   - The `images` field is an **array** of image objects (not a dictionary)
   - Append a new image object to the array for each downloaded image:
   ```json
   {
     "camp_name": "Camp Bird of Paradise",
     "images": [
       {
         "filename": "instagram_20250129_143052_photo1.jpg",
         "source_page_url": "https://www.instagram.com/campbirdofparadise",
         "original_filename": "photo1.jpg",
         "download_date": "2025-01-29 14:30:52",
         "source": "instagram"
       }
     ]
   }
   ```
   - The curator checks for images where `'curation_result' not in img` to find uncurated images
   - After curation, the curator adds `curated_date` and `curation_result` fields to each image

6. **Update download_state.json**
   - Load `images/scraper/download_state.json`
   - Update or create entry for this camp under `state['camps'][camp_name]`:
   ```json
   {
     "camps": {
       "Camp Bird of Paradise": {
         "urls_provided": ["https://www.instagram.com/campbirdofparadise"],
         "urls_checked": ["https://www.instagram.com/campbirdofparadise"],
         "social_media_urls": ["https://www.instagram.com/campbirdofparadise"],
         "error_urls": [],
         "redirected_urls": {},
         "images_downloaded": 2,
         "status": "success",
         "last_processed": "2025-01-29 14:30:52"
       }
     }
   }
   ```
   - If the camp already exists in download_state.json, merge the new URLs into existing lists and increment `images_downloaded`
   - The curator uses `last_processed` vs `last_curated` to detect camps needing re-curation

#### Step 2.7: Update Snapshot
- Record current state of Downloads folder for next iteration
- This ensures files downloaded for Camp A aren't re-processed for Camp B

#### Step 2.8: Log Completion
```
  ✓ Processed 3 new images for Camp Bird of Paradise
  Next: Khaleeya (2 of 47)
```

### Phase 3: Completion

After all camps processed (or user Ctrl+C):

```
══════════════════════════════════════════════════════════════════
Session Complete
══════════════════════════════════════════════════════════════════
Camps processed: 47
Total images collected: 127
Images by platform:
  Instagram: 127

To resume later, use:
  python3 scrape_socials.py --start-camp "Last Camp Name"

Next step: Run the curator to review candidates
  python3 curator.py
══════════════════════════════════════════════════════════════════
```

## Graceful Interruption Handling

When user presses Ctrl+C:

1. **If between camps**: Exit cleanly, show resume command
2. **If during image processing**: Complete current image move, then exit
3. **Never leave files in inconsistent state**:
   - Moves are atomic (same filesystem)
   - metadata.json written after successful move
   - Worst case: an image is moved but not in metadata (recoverable)

```python
import signal

def handle_interrupt(signum, frame):
    print("\n\nInterrupted! Finishing current operation...")
    # Set flag to exit after current camp
    global should_exit
    should_exit = True

signal.signal(signal.SIGINT, handle_interrupt)
```

## URL Pattern Matching

### Instagram URL Patterns
```python
INSTAGRAM_PATTERNS = [
    r'instagram\.com/([^/?]+)',           # instagram.com/username
    r'instagr\.am/([^/?]+)',              # Short URL
    r'instagram\.com/p/([^/?]+)',         # Direct post link (extract, but warn)
]
```

### Facebook URL Patterns (Future)
```python
FACEBOOK_PATTERNS = [
    r'facebook\.com/([^/?]+)',            # facebook.com/pagename
    r'fb\.com/([^/?]+)',                  # Short URL
    r'facebook\.com/pages/([^/?]+)',      # Pages URL
]
```

## File Structure

After running, the file structure will look like:

```
images/
└── candidates/
    ├── Camp Bird of Paradise/
    │   ├── metadata.json
    │   ├── instagram_20250129_143052_photo1.jpg
    │   └── instagram_20250129_143055_photo2.jpg
    ├── Khaleeya/
    │   ├── metadata.json
    │   └── instagram_20250129_144012_image.png
    └── ... (other camps)
```

## metadata.json Schema

The `images` field is an **array** of image objects. This matches the format used by the existing scrapers and expected by the curator.

```json
{
  "camp_name": "Camp Bird of Paradise",
  "images": [
    {
      "filename": "instagram_20250129_143052_photo1.jpg",
      "source_page_url": "https://www.instagram.com/campbirdofparadise",
      "original_filename": "photo1.jpg",
      "download_date": "2025-01-29 14:30:52",
      "source": "instagram"
    },
    {
      "filename": "instagram_20250129_143055_photo2.jpg",
      "source_page_url": "https://www.instagram.com/campbirdofparadise",
      "original_filename": "photo2.jpg",
      "download_date": "2025-01-29 14:30:55",
      "source": "instagram",
      "curated_date": "2025-01-30 10:15:00",
      "curation_result": "approved"
    }
  ]
}
```

### Image Object Fields

| Field | Required | Description |
|-------|----------|-------------|
| `filename` | Yes | The filename as stored in the candidates folder |
| `source_page_url` | Yes | The social media page URL where the image was found |
| `original_filename` | Yes | The original filename from the Downloads folder |
| `download_date` | Yes | Timestamp when the image was downloaded (format: "YYYY-MM-DD HH:MM:SS") |
| `source` | Yes | The platform: "instagram", "facebook", "website", or "gallery" |
| `curated_date` | No | Added by curator when image is reviewed |
| `curation_result` | No | Added by curator: "approved" or "rejected" |

### Curator Integration

The curator (`curator_server.py`) identifies uncurated images by checking:
```python
uncurated_images = [
    img for img in metadata.get('images', [])
    if 'curation_result' not in img
]
```

## download_state.json Schema

This file tracks the state of all camps across all scrapers. Each camp entry contains:

```json
{
  "camps": {
    "Camp Name": {
      "urls_provided": ["list of URLs from campHistory.json"],
      "urls_checked": ["list of URLs actually visited"],
      "social_media_urls": ["subset that are social media"],
      "error_urls": ["URLs that failed"],
      "redirected_urls": {"original": "redirected_to"},
      "images_downloaded": 5,
      "status": "success",
      "last_processed": "2025-01-29 14:30:52",
      "last_curated": "2025-01-30 10:15:00"
    }
  }
}
```

The curator uses `last_processed > last_curated` to identify camps that need re-curation after new images are downloaded.

## Error Handling

| Scenario | Handling |
|----------|----------|
| Downloads folder doesn't exist | Exit with error, suggest correct path |
| campHistory.json not found | Exit with error, suggest running from correct directory |
| --start-camp not found | Exit with error, show similar names if possible |
| Image file locked (still downloading) | Skip, will catch on next camp or warn user |
| Permission denied moving file | Warn, leave file in Downloads, continue |
| Disk full | Exit with error after current operation |
| Invalid URL in campHistory | Skip camp with warning, continue |
| Browser fails to launch | Warn, offer to continue (user can manually open URL) |

## Dependencies

```python
# Standard library only - no external dependencies
import json
import os
import shutil
import webbrowser
import signal
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Set
```

## Example Session

```
$ python3 data/scrape_socials.py --platform instagram

Loading camp data...
Found 47 camps with Instagram URLs

══════════════════════════════════════════════════════════════════
Processing: Camp Bird of Paradise (1 of 47 with Instagram)
URL: https://www.instagram.com/campbirdofparadise
══════════════════════════════════════════════════════════════════
Instructions:
  • Browse the page and download any relevant camp images
  • Close the browser tab when done (or press Enter here to continue)
  • Downloaded images will be moved to: images/candidates/Camp Bird of Paradise/

Press Enter when done with this camp (or Ctrl+C to stop)...

  Moved: IMG_1234.jpg → images/candidates/Camp Bird of Paradise/instagram_20250129_143052_IMG_1234.jpg
  Moved: IMG_1235.jpg → images/candidates/Camp Bird of Paradise/instagram_20250129_143052_IMG_1235.jpg
  ✓ Processed 2 new images for Camp Bird of Paradise

══════════════════════════════════════════════════════════════════
Processing: Khaleeya (2 of 47 with Instagram)
URL: https://www.instagram.com/teahivelounge/
══════════════════════════════════════════════════════════════════
...

^C

Interrupted! Finishing current operation...

══════════════════════════════════════════════════════════════════
Session Paused
══════════════════════════════════════════════════════════════════
Camps processed: 2 of 47
Total images collected: 5

To resume, use:
  python3 data/scrape_socials.py --start-camp "Sepia Lux Homebase"
══════════════════════════════════════════════════════════════════
```

## Future Enhancements (Not in Initial Implementation)

1. **Facebook support**: Add URL patterns and handling for Facebook pages
2. **TikTok support**: Similar pattern for TikTok profiles
3. **Progress persistence**: Save state to file for automatic resume
4. **Duplicate detection**: Hash-based detection of already-downloaded images
5. **Thumbnail generation**: Create thumbnails during import for faster curation
6. **Browser extension**: Optional extension to auto-detect tab close and send signal
