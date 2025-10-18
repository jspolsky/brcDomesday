# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BRC Domesday** is an interactive web-based map visualization tool for Burning Man 2025 camp data. It shows a detailed map of Burning Man where you can mouse over any camp and see information about that camp.

In building the app, we discovered a problem. 

### The Problem
- `camp_outlines_2025.geojson` contains precise polygon boundaries with FID identifiers
- `camp_names_2025.geojson` contains vector paths for text rendering (not OCR-friendly)
- `camps.json` contains full camp metadata (name, description, location string, etc.)
- No automated way exists to match outline FIDs to camp names

The first step in solving this problem was to create an interactive browser which showed the user one camp at a time, and asked them to type in the name of the camp. As the user created the camp names, it built up a file camp_fid_mappings.json which mapped FIDs from camp_outlines to camp names which are almost always found in camps.json.

All that code has been moved into a git branch called createcampnames. It's not present in the main branch any more. Now the main branch is a nice browser that relies on an already-constructed FID->Camp mapping.

## Architecture

### Frontend (Vanilla JavaScript)
The entire application is a single-page HTML/CSS/JavaScript implementation with no build system:
- `index.html` - HTML structure with map canvas, sidebar, popup, and full-page camp info UI elements
- `map.js` - Main application logic (~1000 lines): rendering, interaction, coordinate transforms, event handlers
- `style.css` - Styling for map canvas, status bar, sidebar panels, popups, and overlays
- Canvas-based rendering using HTML5 Canvas API
- Custom geographic coordinate system handling (WGS84 lat/lon to canvas pixels)
- 45-degree rotation transform to orient 12:00 at the top of the map

### Data Files
All data files are located in the `data/` subdirectory:
- `camp_outlines_2025.geojson` (691KB) - Polygon boundaries for ~1000+ camps, each with unique `fid`
- `camp_names_2025.geojson` (24MB) - Vector text paths for camp names (not currently rendered)
- `camps.json` (1.5MB) - Full camp metadata from Burning Man 2025
- `camp_fid_mappings.json` - Human-curated mapping between outline FIDs and camp names
- `campHistory.json` (3.1MB) - Historical camp attendance data (2015-2025, excluding 2020-2021)
- `camps2015.json` through `camps2025.json` - Annual camp data from Burning Man API (source for campHistory.json)
- `BRCMap.pdf` (10MB) - Reference PDF map
- `BRCMapAdj.png` - PNG background image overlay aligned with GeoJSON data

### Additional Assets
- `firstcamp.jpg` - Sample camp image for display in UI

### Python Utilities
Located in the `data/` subdirectory:
- `download_historical_camps.py` - Downloads historical camp data from Burning Man API (2015-2025)
- `build_camp_history.py` - Processes annual camp files to create consolidated campHistory.json
- `README.campHistory` - Specification document for campHistory.json format

## Key Technical Details

### Coordinate System
- **CRS**: WGS84 (EPSG:4326) - standard longitude/latitude
- **Black Rock City bounds**: approximately -119.26 to -119.19 longitude, 40.78 to 40.79 latitude
- **Projection**: Custom Mercator-like scaling with `Math.cos(latitude * π/180)` adjustment for accurate rendering at this latitude

### Map Interaction Features
- **Pan**: Click and drag to pan the map
- **Zoom**: Mouse wheel to zoom in/out (maintains cursor position)
- **Hover**: Displays camp name and location in popup when mouse hovers over a mapped camp
- **Single click**: Opens sidebar with camp details (name, location, description, image)
- **Double click**: Opens full-page camp information view with:
  - Full camp details (name, location, description, image, URL, contact, etc.)
  - Historical attendance section showing years the camp has attended (2015-2024)
  - Interactive year pills with dropdown tooltips showing historical location, description, and archived URL
- **Polygon hit detection**: Ray-casting algorithm (`isPointInPolygon`) for point-in-polygon tests
- **Visual feedback**: Yellow highlight on hovered camps
- **Background image**: PNG overlay of the official BRC map, rotated 45° and aligned with GeoJSON data
- **Keyboard shortcuts**: ESC to close sidebar/full-page view, 'b' to toggle background image

### Core Rendering Flow
1. Load GeoJSON files and JSON data asynchronously (camp outlines, mappings, camp data, camp history)
2. Load background PNG image and align with geographic coordinates
3. Calculate geographic bounds from actual data
4. Render background image (rotated 45°, scaled, and positioned to align with GeoJSON)
5. Render camp outlines as filled polygons (invisible unless showOutlines is true)
6. Apply yellow highlight to hovered camp
7. Handle mouse events for hover detection, popup display, sidebar opening, and full-page view
8. Update viewport on user interaction (pan/zoom)

### Data Processing Patterns
- **FID to camp name lookup**: `camp_fid_mappings.json` maps outline FIDs to camp names as strings
- **Camp data lookup**: Camp names are used to find full camp details in `camps.json` (by matching the `name` field)
- **Historical data lookup**: `campHistory.json` provides year-by-year attendance records keyed by camp name
- **Coordinate transformation**: `geoToCanvas()` and `canvasToGeo()` handle bidirectional conversion with rotation
- **Rotation transform**: 45° clockwise rotation applied to all coordinates to orient 12:00 at top
- **Viewport management**: Maintains center point and scale factor, updates on user interaction
- **Background image alignment**: Complex transform chain (geographic → canvas → rotation → scale → offset) defined in `BACKGROUND_IMAGE_SETTINGS`
- **Wayback Machine links**: Historical URLs redirect to Internet Archive snapshots from August 1st of the relevant year

## Common Development Tasks

### Running the Application
```bash
# No build step required - just open in browser
open index.html

# Or use any local server (required for loading local data files in some browsers):
python3 -m http.server 8000
# Then navigate to http://localhost:8000
```

### Updating Historical Camp Data
```bash
cd data

# Download latest camp data from Burning Man API
python3 download_historical_camps.py YOUR_API_KEY

# Rebuild the consolidated history file
python3 build_camp_history.py
```

### Working with the Data
The GeoJSON structure is consistent across files:
```javascript
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": { "fid": <number>, "Layer": "Camp Outlines" },
      "geometry": { "type": "LineString", "coordinates": [[lon, lat], ...] }
    }
  ]
}
```

**Important**: Despite being labeled "LineString", camp outlines are actually closed polygons (first coordinate == last coordinate).

### Camp Data Structure (camps.json)
```javascript
{
  "uid": "unique_id",
  "name": "Camp Name",
  "location_string": "B & 7:45",  // Street intersection
  "description": "...",
  "hometown": "...",
  // ... more metadata
}
```

### FID Mapping Structure (camp_fid_mappings.json)
```javascript
{
  "1": "Illumination Village",
  "2": "Shipwreck Tiki Lounge",
  // Maps outline FID (as string) to exact camp name from camps.json
}
```

### Camp History Structure (campHistory.json)
```javascript
{
  "Camp Name": {
    "name": "Camp Name",
    "history": [
      {
        "year": 2025,
        "description": "Current year description...",
        "location_string": "D & 3:15",
        "url": "https://example.com"
      },
      {
        "year": 2024,
        "description": "Previous year description...",
        "location_string": "C & 3:00",
        "url": null
      }
      // Sorted by year descending, excludes 2020-2021
    ]
  }
}
```

## Critical Implementation Notes

### Canvas Coordinate Math
- X-axis (longitude): increases westward (negative values become less negative going right)
- Y-axis (latitude): increases northward, but canvas Y increases downward (requires negation)
- Scale factor must account for latitude compression using `latScale = cos(centerY * π/180)`
- **Rotation**: All coordinates rotated 45° clockwise around canvas center using rotation matrix
- Rotation constants: `COS_ROTATION = cos(-45°)`, `SIN_ROTATION = sin(-45°)`
- Transform order: geographic → relative position → rotation → canvas position

### Performance Considerations
- `camp_names_2025.geojson` is 24MB - currently not rendered in the main branch
- Point-in-polygon tests run on every mouse move for hover detection
- Background image is large (BRCMapAdj.png) - loaded once and cached by browser
- Camp outlines rendered as invisible hit-test areas unless `showOutlines` is enabled

### UI State Management
The application maintains several state variables in `map.js`:
- `highlightedCamp` - Currently hovered camp (for yellow highlight)
- `currentPopupCampName` - Camp shown in small hover popup
- `sidebarOpen` / `currentSidebarCampName` - Sidebar state and content
- `sidebarOnLeft` - Dynamic sidebar positioning based on mouse position
- `fullCampInfoOpen` / `currentFullCampName` - Full-page view state
- `showBackgroundImage` - Toggle for background map visibility
- `showOutlines` - Toggle for camp outline visibility (debugging)

### Key Functions in map.js
- `geoToCanvas(lon, lat)` - Converts WGS84 coordinates to canvas pixel position (with rotation)
- `canvasToGeo(x, y)` - Inverse transform from canvas to geographic coordinates
- `isPointInPolygon(lon, lat, coords)` - Ray-casting algorithm for hit detection
- `findCampAtLocation(lon, lat)` - Returns camp FID at given geographic coordinate
- `getCampByName(name)` - Looks up full camp data from camps.json by name
- `showCampPopup(campName)` - Displays hover popup with camp name/location
- `showCampSidebar(campName, mouseX)` - Opens sidebar with camp details (positioned left/right based on mouseX)
- `showFullCampInfo(campName)` - Opens full-page camp information view
- `buildCampHistorySection(campName)` - Generates historical attendance section with interactive year pills
- `showHistoryTooltip(event)` - Displays dropdown tooltip with historical camp details
- `positionTooltip(target, tooltip)` - Smart positioning for tooltips (below or above target)
- `redraw()` - Main render function that draws background, outlines, and highlights

## Project Context

The main branch now contains a fully functional interactive camp browser that:
1. Displays all Burning Man 2025 camps on an accurate map
2. Shows camp details when users hover or click on camp boundaries
3. Provides three levels of detail: popup (hover), sidebar (click), full-page (double-click)
4. Uses the completed `camp_fid_mappings.json` to connect outline polygons to camp metadata

The earlier tool for building the FID mappings has been moved to the `createcampnames` branch.

## Git Workflow

- **Main branch**: Production-ready interactive camp browser
- **createcampnames branch**: Historical tool for building FID mappings (archived)
- `.gitignore` excludes `.DS_Store` files
