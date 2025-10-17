#!/usr/bin/env python3
import json
import sys

def find_unclosed_polygons(geojson_file):
    with open(geojson_file, 'r') as f:
        data = json.load(f)
    
    unclosed = []
    tolerance = 0.000001
    
    for feature in data['features']:
        if feature['geometry']['type'] == 'LineString':
            coords = feature['geometry']['coordinates']
            if len(coords) > 3:
                first = coords[0]
                last = coords[-1]
                
                # Check if closed with same tolerance as our JavaScript
                is_closed = (abs(first[0] - last[0]) < tolerance and 
                           abs(first[1] - last[1]) < tolerance)
                
                if not is_closed:
                    fid = feature['properties']['fid']
                    unclosed.append({
                        'fid': fid,
                        'first': first,
                        'last': last,
                        'coords_count': len(coords)
                    })
    
    return unclosed

if __name__ == "__main__":
    unclosed = find_unclosed_polygons('data/camp_outlines_2025.geojson')
    
    print(f"Found {len(unclosed)} unclosed polygons:")
    for item in unclosed:
        print(f"FID {item['fid']}: first={item['first']}, last={item['last']}, coords={item['coords_count']}")