# Image Curator

Web-based interface for reviewing and approving candidate camp images.

## Setup

Install dependencies:

```bash
pip3 install -r requirements.txt
```

## Usage

Start the curator server:

```bash
python3 curator_server.py
```

Then open http://localhost:8080 in your web browser.

## How to Curate

1. The app automatically loads the next camp that needs curation
2. Review the camp name, description, and website link
3. All images start as **accepted** by default
4. **Click any image** to reject it (adds 🚫 and makes it 50% transparent)
5. **Click again** to un-reject (toggle behavior)
6. Use **Reject All** button to mark all images for rejection
7. Use **Accept All** button to clear all rejections
8. Click **Submit Curation** when done
9. The app automatically loads the next camp

## Keyboard Shortcuts

- **Cmd/Ctrl + Enter**: Submit curation

## What Gets Saved

When you submit:

1. **metadata.json** in each camp's candidates folder is updated with:
   - `curated_date`: Timestamp when curated
   - `curation_result`: Either "approved" or "rejected"

2. **download_state.json** is updated with:
   - `last_curated`: Timestamp when this camp was last curated

## Curation Guidelines

**Approve images that:**
- Clearly show the camp or camp activities
- Are good quality and well-lit
- Represent the camp's character/theme
- Would be useful for users browsing the map

**Reject images that:**
- Don't show the camp
- Are too dark, blurry, or low quality
- Are primarily of people (privacy concerns)
- Are generic stock photos or website UI elements
- Contain inappropriate content

## Technical Details

The curator consists of:
- **curator_server.py**: Flask backend that serves the UI and provides API endpoints
- **static/index.html**: Main HTML interface
- **static/style.css**: Styling with 3-column responsive grid
- **static/curator.js**: JavaScript for image loading, interaction, and API calls

### API Endpoints

- `GET /api/next-camp`: Returns next uncurated camp data
- `POST /api/curate`: Saves curation decisions
- `GET /candidates/<path>`: Serves candidate images
