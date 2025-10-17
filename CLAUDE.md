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
- `index.html` - Complete interactive map viewer (~650 lines of inline JavaScript)
- `style.css` - Minimal styling for map canvas and controls
- Canvas-based rendering using HTML5 Canvas API
- Custom geographic coordinate system handling (WGS84 lat/lon to canvas pixels)

### Data Files
- `data/camp_outlines_2025.geojson` (691KB) - Polygon boundaries for ~1000+ camps, each with unique `fid`
- `data/camp_names_2025.geojson` (24MB) - Vector text paths for camp names
- `data/camps.json` (1.5MB) - Full camp metadata from Burning Man API
- `data/camp_fid_mappings.json` - Human-curated mapping between outline FIDs and camp names
- `data/BRCMap.pdf` (10MB) - Reference map

### Python Utilities
- `find_unclosed.py` - Diagnostic tool to find polygon closure issues in GeoJSON
- `fix_polygons.py` - Repairs unclosed polygons by appending the first coordinate to close them

## Key Technical Details

### Coordinate System
- **CRS**: WGS84 (EPSG:4326) - standard longitude/latitude
- **Black Rock City bounds**: approximately -119.26 to -119.19 longitude, 40.78 to 40.79 latitude
- **Projection**: Custom Mercator-like scaling with `Math.cos(latitude * π/180)` adjustment for accurate rendering at this latitude

### Map Interaction Features
- **Pan**: Click and drag to pan the map
- **Zoom**: Mouse wheel to zoom in/out (maintains cursor position)
- **Hover**: Displays camp FID when mouse hovers over a polygon
- **Polygon hit detection**: Ray-casting algorithm (`isPointInPolygon`) for point-in-polygon tests
- **Visual feedback**: Yellow highlight on hovered camps, red stars mark unclosed polygons

### Core Rendering Flow
1. Load GeoJSON files asynchronously
2. Calculate geographic bounds from actual data
3. Render camp outlines as stroked paths (lightblue)
4. Optionally render camp names as black vector paths
5. Highlight unclosed polygons with red star markers at centroids
6. Update viewport on user interaction (pan/zoom)

### Data Processing Patterns
- **Polygon closure validation**: Uses 0.000001 tolerance to check if first/last coordinates match
- **Centroid calculation**: Simple arithmetic mean of all polygon coordinates
- **Coordinate transformation**: `geoToCanvas()` and `canvasToGeo()` handle bidirectional conversion
- **Viewport management**: Maintains center point and scale factor, updates on user interaction

## Common Development Tasks

### Running the Application
```bash
# No build step required - just open in browser
open index.html
# Or use any local server:
python3 -m http.server 8000
```

### Fixing Broken Polygon Data
```bash
# Find unclosed polygons
python3 find_unclosed.py

# Fix specific polygons (edit FID list in script first)
python3 fix_polygons.py
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

## Critical Implementation Notes

### Canvas Coordinate Math
- X-axis (longitude): increases westward (negative values become less negative going right)
- Y-axis (latitude): increases northward, but canvas Y increases downward (requires negation)
- Scale factor must account for latitude compression using `latScale = cos(centerY * π/180)`

### Performance Considerations
- `camp_names_2025.geojson` is 24MB - loading is async with status indicator
- Rendering 27,764+ name features can be slow - toggle visibility for performance
- Point-in-polygon tests run on every mouse move - optimized with early exits

### Known Issues & Fixes
- Some camp outline polygons were unclosed (first != last coordinate)
- Fixed polygons: FIDs 223, 1076, 1274, 1276 (see git history)
- Fix approach: append first coordinate to end of coordinate array

## Project Context

This tool enables human volunteers to:
1. Hover over a camp outline on the map
2. See the FID displayed
3. Visually identify which camp it is (from context/neighbors)
4. Manually record the mapping in `camp_fid_mappings.json`

The eventual goal is to build a complete mapping that other applications can use to display camp names with their precise boundaries.

## Git Workflow

- Main branch: (not configured - working on `explorer` branch)
- Recent work: fixing polygon outlines, adding FID display, importing camp mappings
- Clean working directory with `.gitignore` for `.DS_Store` files
