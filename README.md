# BRC Domesday Book

An interactive map viewer for Burning Man 2025 theme camps. Requires a desktop web browser... this is too fancy for your little phone, sorry.

## Features

**Explore the Map**
- Pan by clicking and dragging
- Zoom with mouse wheel or pinching on the trackpad.
- Click **Zoom to Fit** to reset view

**Discover Camps**
- **Hover** over any camp to see its name and location
- **Click** once to open a sidebar with camp details
- **Double-click** for full-screen camp information including:
  - Photos and descriptions
  - Contact information and website
  - Location and landmark details
  - Historical attendance data (2015-2024)

**Historical Data**
- View which years each camp has attended Burning Man
- Hover over any historical year to see that year's location, description, and website
- Click historical URLs to view archived snapshots via the Wayback Machine

## Navigation

- **ESC** or click **×** to Close sidebar or full-screen view

## Data

- **Camp Information**: Official Burning Man 2025 camp placement data
- **Historical Records**: Camp attendance from 2015-2024 (excluding 2020-2021)
- **Map Accuracy**: GeoJSON polygon boundaries aligned with official BRC coordinates
- **Orientation**: 12:00 positioned at the top of the map, rotating 45° from standard north-up orientation

## Running Locally

No build required. Just open `index.html` in a web browser, or:

```bash
python3 -m http.server 8000
```

Then navigate to `http://localhost:8000`

## Technical Notes

This is a vanilla JavaScript application with no frameworks or dependencies. All rendering uses HTML5 Canvas with custom geographic projections for accurate Black Rock City coordinates.

**For Developers**: See `CLAUDE.md` for architecture details and development guidance.

## createcampnames Branch

Camp borders come from `https://innovate.burningman.org/dataset/2025-public-camps-map/`. As of 2025 there is no official dataset associating camp borders with camp names. The camp borders are associated with consecutive camp numbers (1..1400) called FIDs which are not actually meaningful and do not correspond to anything else in the Burning Man API. There is an official map, but that only contains camp names as vectors of the camp name letters, which are placed in a way that is convenient for reading a map but not computer-readable or OCRable. Thus we built a tool called createcampnames which lives on a branch.

The `createcampnames` branch contains a historical tool used to build the initial FID-to-camp-name mapping. It provided an interactive interface for human volunteers to manually identify and name each camp polygon. This mapping work is complete, and the main branch now uses the finished `camp_fid_mappings.json` file.