# Camp Image Collection Project

## Overview

This subproject aims to significantly expand the image coverage for Burning Man theme camps by automatically discovering, downloading, and curating images from camp websites and other online sources.

## Current State

The BRC Domesday application currently has limited image coverage:
- Most camps have **zero images**
- Some camps have **one image** (when `camps.json` contains a `thumbnail_url`)
- Images are only available when explicitly provided in the camp data from the Burning Man API

## Project Goals

1. **Discover camp images** from multiple sources:
   - Primary: Camp websites (from the `url` field in `camps.json`)
   - Future: Web galleries, social media, photo archives, etc.

2. **Download candidate images** automatically while:
   - Being respectful of servers (rate limiting)
   - Filtering for likely camp-related images (not generic site elements)
   - Supporting interruption and resumption

3. **Human curation workflow** to review and approve images:
   - Simple web-based interface
   - Quick approve/reject decisions
   - Build final curated image dataset

## Architecture

### Component 1: Image Scraper Script

**Purpose**: Discover and download candidate images from camp websites

**Key Features**:
- **Resumability**: Can be interrupted and restarted at any time
- **Progress tracking**: Maintains state of which camps have been processed
- **Rate limiting**: Respectful delays between requests
- **Smart filtering**: Download only images likely to be camp photos (not logos, icons, buttons)
- **Metadata tracking**: Record source URL, download date, camp association

**Input**:
- `campHistory.json` containing camp names and website URLs
- Note that camps may have been coming to Burning Man for one or more years, and may have different URLs for each year, but it's all the same camp.

**Output**:
- Downloaded images organized by camp
- Metadata JSON file tracking download status and image sources (keep original page URL where the image came from so we can go back there)

**Implementation Considerations**:
- May run for hours or days depending on number of camps
- Should handle network failures gracefully
- Should respect `robots.txt`
- Should identify and skip non-photo images (small icons, UI elements, etc.)
- Should handle various website structures (static pages, galleries, etc.)
- Set a limit of about 100 images per camp
- Many camps have Instagram or Facebook URLs. **These may require special consideration** for downloading images. For now, store a list of all the camps with Facebook or Instagram URLs, but we won't attempt to download those images until a future update.

### Component 2: Image Curation Web App

**Purpose**: Allow human review and approval of candidate images

**Key Features**:
- **Simple UI**: Show one image at a time with camp context and where the image came from 
- **Quick decisions**: Keyboard shortcuts for approve/reject
- **Progress tracking**: Show how many images reviewed, remaining
- **Context display**: Show camp name, year, source URL
- **Resume capability**: Remember which images have been reviewed

**Workflow**:
1. Display candidate image
2. Show camp name and other context
3. User decides: Approve, Reject, or Skip (decide later)
4. If the image was approved, add it to the approved image dataset.
5. If the image was approved and it is > 25MB, scale it by reducing the resolution or increasing the compression to get it under 25MB.
6. Move to next image

**Output**:
- Curated list of approved images with camp associations
- Updated camp image dataset ready for integration into main app

## Data Organization

```
images/
├── README.md                      # This file
├── scraper/
│   ├── scrape_images.py          # Main scraper script
│   ├── download_state.json       # Tracks which camps processed
│   └── requirements.txt          # Python dependencies
├── candidates/
│   ├── [camp_name]/               # One directory per camp
│   │   ├── image_00001.jpg
│   │   ├── image_00002.jpg
│   │   └── metadata.json         # Source URLs, download dates
│   └── download_log.json         # Overall download metadata
├── curator/
│   ├── index.html                # Curation web app
│   ├── curator.js                # JavaScript for curation UI
│   ├── style.css                 # Styling
│   └── curation_state.json       # Tracks review progress
└── approved/
    ├── camp_images.json          # Final approved image dataset
    └── [camp_name]/               # Approved images (or symlinks)
        ├── image_00001.jpg
        └── image_00002.jpg
```

## Workflow

### Phase 1: Image Discovery and Download

1. Run scraper script: `python scraper/scrape_images.py`
2. Script processes camps one at a time:
   - Check `download_state.json` to see if already processed
   - Visit camp website URL
   - Parse HTML to find image URLs
   - Filter out small/icon images
   - Download promising images to `candidates/[camp_uid]/`
   - Update `download_state.json`
3. Script can be interrupted (Ctrl+C) and resumed safely

### Phase 2: Human Curation

1. Open curator web app: `file:///.../images/curator/index.html`
2. App loads candidate images from `candidates/` directory
3. For each image:
   - Display image
   - Show camp name and source
   - User clicks Approve, Reject, or Skip
   - State saved to `curation_state.json`
4. Approved images recorded in `approved/camp_images.json`

### Phase 3: Integration

1. Integrate approved images into main BRC Domesday app
2. Update image loading logic to check local approved images
3. Fall back to API thumbnail URLs when available

## Image Selection Heuristics

### For Scraper (Automatic Filtering)

**Include images likely to be**:
- Photos of camps, art installations, structures
- Gallery or photo album images
- Large images (e.g., > 400px in either dimension)
- Image filenames suggesting camp/playa content

**Exclude images likely to be**:
- Site navigation elements (< 100px)
- Social media icons
- Logos, badges
- Background patterns
- Advertisement images

### For Human Curator (Manual Review)

**Approve images that**:
- Clearly show the camp or camp activities
- Are good quality and well-lit
- Represent the camp's character/theme
- Would be useful for users browsing the map

**Reject images that**:
- Don't show the camp
- Are too dark, blurry, or low quality
- Are primarily of people (privacy concerns)
- Are generic stock photos
- Contain inappropriate content

## Technical Considerations

### Scraper Implementation

**Python libraries**:
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `pillow` - Image analysis (size, format)
- `urllib.parse` - URL handling

**Key challenges**:
- Handling JavaScript-rendered galleries (may need Selenium/Playwright)
- Distinguishing camp photos from generic website images
- Managing storage (thousands of images)
- Respecting rate limits and bandwidth

### Curator Implementation

**Technology**:
- Vanilla HTML/CSS/JavaScript (no build required)
- Local file access (may need local server for security)
- JSON for state management

**Key challenges**:
- Loading images from local filesystem
- Efficiently handling large numbers of images
- Keyboard shortcuts for speed
- Saving review state reliably

## Future Enhancements

1. **Additional image sources**:
   - Flickr galleries tagged with camp names
   - Instagram posts (if API available)
   - Burning Man's official photo archives
   - User submissions

2. **Automated quality filtering**:
   - ML-based camp photo detection
   - Automatic duplicate detection
   - Image quality scoring

3. **Multi-image support**:
   - Image carousels in the main app
   - Year-specific images (camp looked different in different years)

4. **Crowd-sourced curation**:
   - Allow multiple reviewers
   - Voting/consensus on image quality
   - Community contributions

## Success Metrics

- **Coverage**: Percentage of camps with at least one image
- **Quality**: Average number of good images per camp
- **Efficiency**: Time to curate 100 images
- **Accuracy**: Percentage of auto-downloaded images that pass human review

## Timeline Estimate

- **Scraper development**: 2-3 days
- **Initial scraping run**: 1-2 days (continuous)
- **Curator app development**: 1-2 days
- **Human curation**: Variable (depends on volume and reviewer time)
- **Integration**: 1 day

## Q&A

1. How many images per camp should we aim for? 
A: For now let's cut it off at 128 images per camp. 

2. What image formats and sizes should we store?
A: We will store the original PNG, JPEG, without changing anything. Do not download any animations or videos.

3. Should we resize images for faster loading?
A: If any image is > 25MB, the curation step should resize it if approved. 

4. How do we handle copyright/attribution?
A: When the image is downloaded, store the URL of the page from whence it was downloaded along with the URL of the image itself, and also a link to any copyright notices that appeared on the original web site. 

5. Should we cache website content to avoid re-downloading?
A: Absolutely!

6. What's the process for updating images annually?
A: For now let's assume this is a one time thing. There will be a future enhancement where we will rerun the scraper once a year and it will only look for new pictures.
