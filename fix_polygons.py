#!/usr/bin/env python3
import json
import sys

def fix_unclosed_polygons(geojson_file):
    # Read the original file
    with open(geojson_file, 'r') as f:
        data = json.load(f)
    
    unclosed_fids = [223, 1076, 1274, 1276]
    fixed_count = 0
    tolerance = 0.000001
    
    for feature in data['features']:
        if feature['geometry']['type'] == 'LineString':
            fid = feature['properties']['fid']
            
            if fid in unclosed_fids:
                coords = feature['geometry']['coordinates']
                if len(coords) > 3:
                    first = coords[0]
                    last = coords[-1]
                    
                    # Check if actually unclosed
                    is_closed = (abs(first[0] - last[0]) < tolerance and 
                               abs(first[1] - last[1]) < tolerance)
                    
                    if not is_closed:
                        # Close the polygon by adding the first coordinate at the end
                        feature['geometry']['coordinates'].append(first)
                        print(f"Fixed FID {fid}: closed polygon with {len(coords)} -> {len(coords)+1} coords")
                        fixed_count += 1
    
    # Write back to file
    with open(geojson_file, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    
    print(f"\nFixed {fixed_count} polygons and saved to {geojson_file}")

if __name__ == "__main__":
    fix_unclosed_polygons('data/camp_outlines_2025.geojson')
    print("Done! You can now refresh your web page to see the changes.")