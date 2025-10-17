# BRC Domesday - AI Coding Agent Instructions

## Project Overview

**BRC Domesday** is a geospatial data project containing Burning Man 2025 camp information sourced from [Burning Man's public datasets](https://innovate.burningman.org/dataset/2025-public-camps-map/). The project focuses on processing and working with GeoJSON data representing camp locations and boundaries at Black Rock City.

The goal of this project is to convert the raw camp placement data provided in the .geojson files into something that can be used by other applications to visualize the location of camps at Burning Man. The raw data provided *does* include exact outlines for each camp, unfortunately, that doesn't include the names of the camps. Although there is a file called camp_names_2025.geojson, it doesn't actually contain the names of the camps in text format -- instead it simply contains vectors that correspond to text that would be rendered on a map. These vector paths have not been responsive to OCR so we are going to have to use human-assisted methods to identify which camp name corresponds to which camp outline.

## Core Architecture & Data Structure

### Primary Data Assets
- `data/camp_names_2025.geojson` (24MB) - LineString features representing camp name placements with `fid` and `Layer: "Camp Names"` properties
- `data/camp_outlines_2025.geojson` (691KB) - LineString features representing camp boundary outlines with `fid` and `Layer: "Camp Outlines"` properties  
- `data/BRCMap.pdf` (10MB) - Reference map document

### GeoJSON Structure Patterns
Both datasets follow consistent GeoJSON FeatureCollection format:
```json
{
  "type": "FeatureCollection",
  "name": "camp_[names|outlines]_2025",
  "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
  "features": [
    {
      "type": "Feature", 
      "properties": { "fid": <number>, "Layer": "<Camp Names|Camp Outlines>" },
      "geometry": { "type": "LineString", "coordinates": [...] }
    }
  ]
}
```

## Coordinate System & Geographic Context

- **CRS**: WGS84 (EPSG:4326) using longitude/latitude coordinates
- **Location**: Black Rock Desert, Nevada (approximately -119.19 to -119.26 longitude, 40.78 to 40.79 latitude)
- **Scale**: High-precision coordinates representing camp-level placement accuracy

## Development Guidelines

### Working with GeoJSON Data
- Files are large (especially camp_names at 24MB) - use streaming parsers for full processing
- Each feature has minimal properties (just `fid` and `Layer`) - spatial relationships are primary
- LineStrings represent text placement paths (names) and boundary polygons (outlines), not linear features
- Features use sequential `fid` numbering starting from 1

### Data Processing Considerations
- Coordinate precision is very high (15+ decimal places) suitable for sub-meter accuracy
- Both datasets cover the same geographic extent but serve different purposes
- Camp names features (27,764 features) significantly outnumber outline features
- Single-point features exist (some camp_names features have identical start/end coordinates)

### Common Operations
- **Spatial analysis**: Use coordinate-based filtering for geographic regions
- **Data visualization**: Consider coordinate density when rendering at different zoom levels  
- **Cross-referencing**: No explicit linking between names and outlines - use spatial joins
- **Performance**: Large dataset size requires efficient parsing and memory management

## File Organization

```
├── data/
│   ├── camp_names_2025.geojson    # Camp name placement data (24MB)
│   ├── camp_outlines_2025.geojson # Camp boundary data (691KB) 
│   └── BRCMap.pdf                 # Reference map
└── .github/
    └── copilot-instructions.md    # This file
```

## Key Technical Notes

- No build system or dependencies currently - pure data repository
- Git history shows single commit from Burning Man data source
- Project name "BRC Domesday" suggests comprehensive cataloging (like the historical Domesday Book)
- Data represents public camp information only - no private/confidential data included