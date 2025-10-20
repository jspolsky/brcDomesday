#!/usr/bin/env python3
"""
Image Curator Server

A Flask-based web server for curating candidate camp images.

Usage:
    python curator_server.py
    Then open http://localhost:8080 in your browser
"""

from flask import Flask, jsonify, request, send_from_directory, send_file
from pathlib import Path
import json
import time
from datetime import datetime

app = Flask(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
SCRAPER_DIR = BASE_DIR / "scraper"
CANDIDATES_DIR = BASE_DIR / "candidates"
DOWNLOAD_STATE_FILE = SCRAPER_DIR / "download_state.json"
CAMPS_JSON = BASE_DIR.parent / "data" / "camps.json"

def load_download_state():
    """Load the scraper's download state."""
    with open(DOWNLOAD_STATE_FILE, 'r') as f:
        return json.load(f)

def save_download_state(state):
    """Save the scraper's download state."""
    with open(DOWNLOAD_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def load_camps_data():
    """Load the camps.json data for descriptions."""
    with open(CAMPS_JSON, 'r') as f:
        camps_list = json.load(f)
    # Convert list to dict keyed by name
    return {camp['name']: camp for camp in camps_list if 'name' in camp}

def get_next_uncurated_camp():
    """Find the next camp that needs curation."""
    state = load_download_state()

    for camp_name, camp_data in sorted(state['camps'].items()):
        # Skip if no images
        if camp_data.get('images_downloaded', 0) <= 1:
            continue

        # Check if needs curation (never curated or scraped since last curation)
        last_processed = camp_data.get('last_processed')
        last_curated = camp_data.get('last_curated')

        if not last_curated or last_processed > last_curated:
            # Load metadata to get image details
            camp_dir = CANDIDATES_DIR / camp_name
            metadata_file = camp_dir / "metadata.json"

            if not metadata_file.exists():
                continue

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Check if there are any uncurated images
            uncurated_images = [
                img for img in metadata.get('images', [])
                if 'curation_result' not in img
            ]

            if uncurated_images:
                return camp_name, metadata

    return None, None

@app.route('/')
def index():
    """Serve the main curator interface."""
    return send_file('static/index.html')

@app.route('/api/next-camp')
def next_camp():
    """Get the next camp that needs curation."""
    camp_name, metadata = get_next_uncurated_camp()

    if not camp_name:
        return jsonify({'status': 'complete', 'message': 'All camps curated!'})

    # Load camps.json to get 2025 description
    camps_data = load_camps_data()
    camp_info = camps_data.get(camp_name, {})

    # Get download state for URLs
    state = load_download_state()
    camp_state = state['camps'].get(camp_name, {})

    return jsonify({
        'status': 'ok',
        'camp_name': camp_name,
        'description': camp_info.get('description', ''),
        'url': camp_info.get('url', ''),
        'images': metadata.get('images', []),
        'urls_checked': camp_state.get('urls_provided', [])
    })

@app.route('/api/curate', methods=['POST'])
def curate():
    """Save curation results for a camp."""
    data = request.json
    camp_name = data.get('camp_name')
    decisions = data.get('decisions')  # Dict of filename -> 'approved' or 'rejected'

    if not camp_name or not decisions:
        return jsonify({'status': 'error', 'message': 'Missing camp_name or decisions'}), 400

    # Update metadata.json
    camp_dir = CANDIDATES_DIR / camp_name
    metadata_file = camp_dir / "metadata.json"

    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    # Update each image with curation results
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for img in metadata['images']:
        filename = img['filename']
        if filename in decisions:
            img['curated_date'] = timestamp
            img['curation_result'] = decisions[filename]

    # Save updated metadata
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Update download_state.json with last_curated timestamp
    state = load_download_state()
    if camp_name in state['camps']:
        state['camps'][camp_name]['last_curated'] = timestamp
    save_download_state(state)

    return jsonify({'status': 'ok', 'message': f'Curated {len(decisions)} images for {camp_name}'})

@app.route('/candidates/<path:filepath>')
def serve_candidate_image(filepath):
    """Serve candidate images."""
    return send_from_directory(CANDIDATES_DIR, filepath)

@app.route('/static/<path:filepath>')
def serve_static(filepath):
    """Serve static files (HTML, CSS, JS)."""
    return send_from_directory('static', filepath)

if __name__ == '__main__':
    print("="*80)
    print("BRC Domesday Image Curator")
    print("="*80)
    print()
    print("Starting server on http://localhost:8080")
    print("Open this URL in your web browser to begin curation.")
    print()
    print("Press Ctrl+C to stop the server.")
    print("="*80)

    app.run(host='localhost', port=8080, debug=True)
