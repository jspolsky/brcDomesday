#!/usr/bin/env python3
"""
Personality Quiz Web App for BRC Camp Recommendations

A fun, BuzzFeed-style personality quiz that matches users to camps
based on their personality traits.

Usage:
    python3 personality_quiz_app.py
    Then open http://localhost:5001 in your browser
"""

from flask import Flask, render_template, request, jsonify
from pathlib import Path
import json
from rank_camps_personality import PersonalityCampRanker, PersonalityProfile

app = Flask(__name__)

# Initialize ranker (load once at startup)
print("Initializing personality-based camp ranker...")
ranker = PersonalityCampRanker()
print("Ready!")

# Load full camp data for enrichment
print("Loading full camp data...")
with open(Path(__file__).parent.parent / 'data' / 'camps.json') as f:
    camps_data = json.load(f)

# Create lookup by name
camps_by_name = {}
for camp in camps_data:
    # Normalize name for matching
    name_normalized = camp['name'].lower().strip()
    camps_by_name[name_normalized] = camp

print(f"Loaded {len(camps_by_name)} camps for enrichment")


@app.route('/')
def index():
    """Serve the personality quiz interface"""
    return render_template('personality_quiz.html')


@app.route('/api/rank_personality', methods=['POST'])
def rank_personality():
    """
    API endpoint to rank camps based on personality traits.

    Expects JSON with personality scores (0-100):
    {
        "high_energy_social": 90,
        "early_bird": 30,
        "hands_on_maker": 80,
        ...
    }

    Returns JSON with ranked camps
    """
    data = request.json

    # Create personality profile from traits
    profile = PersonalityProfile(**data)

    # Get rankings
    results = ranker.rank(profile, top_k=50)

    # Enrich results with full camp data
    enriched_results = []
    for result in results:
        name_normalized = result['name'].lower().strip()
        camp = camps_by_name.get(name_normalized, {})

        enriched = {
            **result,
            'description': camp.get('description', 'No description available.'),
            'location_string': camp.get('location_string', 'Location TBD'),
            'url': camp.get('url'),
            'images': camp.get('images', [])
        }
        enriched_results.append(enriched)

    return jsonify({
        'success': True,
        'results': enriched_results
    })


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🔥 BURNING MAN PERSONALITY QUIZ 🔥")
    print("=" * 80)
    print("\nStarting web server...")
    print("Open your browser to: http://localhost:5001")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 80 + "\n")

    app.run(debug=True, port=5001)
