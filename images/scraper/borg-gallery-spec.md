# Burning Man Gallery Scraper - Specification

## Research Findings

### Search Results Structure
- **No results**: Shows message "No results for that search. Try something weirder."
- **With results**: Displays 24 images per page in a masonry grid
- **Pagination**: Uses infinite scroll with URL parameter `?q=[query]&p=[pageNumber]`
- **Metadata visible in search results**:
  - Image title (e.g., "Black Rock Roller Disco 2013")
  - Photographer credit (e.g., "Photo by: philippe glade - Philippe Glade")
  - Asset ID (UUID in the link URL)
  - Thumbnail URL (300x300px via Widen CDN)

### Asset Detail Pages
- **URL pattern**: `/asset/[UUID]?i=[index]&q=[query]`
- **Additional metadata available**:
  - **Year**: Explicitly listed (e.g., "Year: 2013")
  - **Photo credit**: Full photographer attribution
  - **Caption/title**: Image description
- **Image access**: Uses lazy-loading JavaScript - full-size URLs not in initial HTML

### Technical Challenges
- Infinite scroll requires pagination via URL parameters (`p=1, p=2, etc.`)
- Images use signed CDN URLs with expiration
- Full-size images require JavaScript rendering (complex) or we can use 300x300 thumbnails (simpler)

---

## DETAILED SPECIFICATION: Burning Man Gallery Scraper

### Purpose
Scrape images from gallery.burningman.org for camps in camps.json, downloading candidate images for curator approval.

### Input
- **Source**: `data/camps.json` - list of all 2025 camps
- **Target**: camps without images or with few images in `campHistory.json`

### Output Structure
```
images/
  candidates/
    [Camp Name]/
      image_00001.jpg
      image_00002.jpg
      image_00003.jpg
      ...
      metadata.json
```

**Note**: If a camp already has images from other sources, the scraper should:
1. Load existing metadata.json
2. Find the highest existing image number
3. Continue numbering from there (e.g., if image_00005.jpg exists, start with image_00006.jpg)

### Metadata Format (metadata.json)

This format matches the existing curator workflow. Gallery-specific fields (photographer, year, caption, asset_id, asset_url) are added to the standard structure.

```json
{
  "camp_name": "Black Rock Roller Disco",
  "images": [
    {
      "filename": "image_00001.jpg",
      "image_url": "https://previews.us-east-1.widencdn.net/preview/19766140/assets/...",
      "source_page_url": "https://gallery.burningman.org/asset/43f2ce01-2d7e-46c1-ba5b-05207b631bdd",
      "original_url": "https://gallery.burningman.org/asset/43f2ce01-2d7e-46c1-ba5b-05207b631bdd",
      "width": 300,
      "height": 300,
      "size_bytes": 45678,
      "download_date": "2025-11-22 10:30:15",
      "photographer": "philippe glade - Philippe Glade",
      "year": 2013,
      "title": "Black Rock Roller Disco 2013",
      "caption": "either for skating or headstand",
      "asset_id": "43f2ce01-2d7e-46c1-ba5b-05207b631bdd"
    }
  ]
}
```

**Field Descriptions:**
- **filename**: Sequential filename (image_00001.jpg, image_00002.jpg, etc.)
- **image_url**: Direct URL to the downloaded thumbnail image (300x300)
- **source_page_url**: The gallery.burningman.org asset detail page (clickable source for this image)
- **original_url**: The gallery.burningman.org asset detail page (same as source_page_url)
- **width/height**: Image dimensions (300x300 for thumbnails)
- **size_bytes**: File size in bytes
- **download_date**: When the image was downloaded (YYYY-MM-DD HH:MM:SS format)
- **photographer**: Photo credit from gallery (NEW - gallery-specific)
- **year**: Year the photo was taken (NEW - gallery-specific)
- **title**: Image title from gallery (NEW - gallery-specific)
- **caption**: Image caption/description (NEW - gallery-specific)
- **asset_id**: Gallery asset UUID (NEW - gallery-specific)

**Curation fields** (added by curator later):
- **curated_date**: When the image was curated
- **curation_result**: "approved" or "rejected"

### Algorithm

#### Phase 1: Iterate Through Camps
```
FOR each camp in camps.json:
  1. Get camp name
  2. Check if images/candidates/[camp_name]/metadata.json exists
  3. If exists:
     - Load existing metadata
     - Extract existing asset_ids to avoid duplicates
     - Determine next image sequence number
  4. If not exists:
     - Create new metadata structure: {"camp_name": "...", "images": []}
     - Start sequence at 1
  5. Call search_gallery(camp_name)
  6. Wait 10-15 seconds between camps (rate limiting)
```

#### Phase 2: Search Gallery
```
search_gallery(camp_name):
  1. URL-encode camp name
  2. Fetch https://gallery.burningman.org/search/?q=[encoded_name]
  3. Parse HTML to check for "No results for that search"
     - If found: return (skip this camp)
  4. Extract all image results from page
  5. Check for additional pages (p=2, p=3, etc.)
  6. FOR each page:
     - Extract image results
     - Wait 2-3 seconds between pages
  7. Process all collected results
```

#### Phase 3: Extract Image Data from Search Results
```
FOR each image result in search results:
  1. Extract from HTML:
     - asset_id (from href="/asset/[UUID]...")
     - photographer (from "Photo by: ..." text)
     - title (from link text)
  2. Get asset detail page: /asset/[asset_id]
  3. Extract additional metadata:
     - year (from "Year: YYYY")
     - caption (from image description)
  4. Wait 1-2 seconds between detail page fetches
```

#### Phase 4: Download Images
```
FOR each image:
  1. Check if total images for this camp >= 128
     - If so: skip remaining images, move to next camp
  2. Check if already downloaded (by asset_id in existing metadata.json)
  3. If not downloaded:
     - Create directory: images/candidates/[camp_name]/ (if needed)
     - Determine next sequential filename:
       * Load existing metadata.json if it exists
       * Find highest image_NNNNN number
       * Use next number for new images
     - Download thumbnail (300x300) from thumbnail_url
     - Save as: image_NNNNN.jpg (e.g., image_00001.jpg)
     - Get file size and dimensions
     - Update metadata.json with complete image info
     - DO NOT add curation fields yet (curator adds those)
  4. Wait 1-2 seconds between downloads
```

**Image Limit**: Maximum 128 images per camp to avoid excessive downloads for very popular camps.

### Image Resolution Strategy

**Option A: Thumbnail-only (Recommended for MVP)**
- Download 300x300px thumbnails directly from search results
- Pros: Simple, fast, no JavaScript required
- Cons: Lower resolution
- Good for: Initial preview and curation workflow

**Option B: Full-size images (Future enhancement)**
- Use browser automation (Selenium/Playwright) to render asset pages
- Extract full-size image URLs from JavaScript-loaded content
- Pros: High-resolution images
- Cons: Complex, slower, more fragile

**Recommendation**: Start with Option A, add Option B later if needed.
**ACCEPTED** we will use thumbnails

### Rate Limiting & Politeness
- **Between camps**: 10-15 seconds
- **Between search result pages**: 2-3 seconds
- **Between asset detail fetches**: 1-2 seconds
- **Between image downloads**: 1-2 seconds
- **User-Agent**: Identify as research scraper with contact info 
- **Respect robots.txt**: Check for restrictions

### Error Handling
1. **Network errors**: Retry up to 3 times with exponential backoff
2. **404 on asset pages**: Log warning, skip image, continue
3. **Rate limiting (429)**: Wait 60 seconds, retry
4. **Parse errors**: Log error, skip image, continue
5. **Failed downloads**: Log error, mark in metadata, continue

### Logging
- Log to: `data/gallery_scraper.log`
- Log levels:
  - INFO: Camp processed, images found/downloaded
  - WARNING: Missing metadata, parse errors
  - ERROR: Network failures, file I/O errors
- Progress indicators:
  - "Processing camp X of Y: [Camp Name]"
  - "Found N images, downloading M new ones"

### Script Interface
```bash
python3 scrape_gallery.py [options]

Options:
  --camp "Camp Name"    # Process single camp only
  --limit N             # Process only first N camps
  --skip-existing       # Skip camps that already have gallery images
  --max-images N        # Download max N images per camp (default: 128)
  --delay SECONDS       # Override default delay between camps
  --dry-run             # Show what would be done without downloading
```

### Dependencies
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `urllib.parse` - URL encoding
- Standard library: `json`, `pathlib`, `time`, `logging`

### Testing Strategy
Before running on all camps:
1. Test with "Black Rock Roller Disco" (known to have results)
2. Test with a fake camp name (test no-results handling)
3. Test with "Center Camp" (large result set, test pagination)
4. Verify metadata.json format
5. Verify image downloads work
6. Verify rate limiting delays

---

## Next Steps

1. Review and approve this specification
2. Implement the scraper following this design
3. Test with sample camps
4. Run on full dataset with appropriate delays
5. Build curation interface to review downloaded images
