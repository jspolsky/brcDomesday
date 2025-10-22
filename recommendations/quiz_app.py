#!/usr/bin/env python3
"""
Standalone Quiz Web App for BRC Camp Recommendations

A simple Flask web app that presents an interactive quiz to collect user
preferences and returns ranked camp recommendations.

Usage:
    python3 quiz_app.py
    Then open http://localhost:5000 in your browser
"""

from flask import Flask, render_template, request, jsonify
from pathlib import Path
import json
from rank_camps import CampRanker, UserProfile

app = Flask(__name__)

# Initialize ranker (load once at startup)
print("Initializing camp ranker...")
ranker = CampRanker()
print("Ready!")

# Load full camp data for display
print("Loading full camp data...")
with open(Path(__file__).parent.parent / 'data' / 'camps.json') as f:
    camps_data = json.load(f)

# Create lookup by UID
camps_by_uid = {camp['uid']: camp for camp in camps_data}
print(f"Loaded {len(camps_by_uid)} camps")


@app.route('/')
def index():
    """Serve the quiz interface"""
    return render_template('quiz.html')


@app.route('/api/rank', methods=['POST'])
def rank():
    """
    API endpoint to rank camps based on user preferences.

    Expects JSON with:
    {
        "sound_party": 0-100 or null,
        "hospitality": 0-100 or null,
        "workshops": 0-100 or null,
        "woo_woo": 0-100 or null,
        "art": 0-100 or null,
        "queer": 0-100 or null,
        "sober": 0-100 or null,
        "family": 0-100 or null,
        "description": "optional text" or null,
        "hometown": "optional hometown" or null
    }

    Returns JSON with ranked camps
    """
    data = request.json

    # Extract description and hometown separately
    description = data.get('description')
    hometown = data.get('hometown')

    # All other fields are axis preferences
    axes = {k: v for k, v in data.items() if k not in ['description', 'hometown'] and v is not None}

    # Create user profile with flexible axes
    profile = UserProfile(
        description=description,
        hometown=hometown,
        **axes
    )

    # Get rankings
    results = ranker.rank(profile, top_k=50)

    # Enrich results with full camp data
    enriched_results = []
    for result in results:
        uid = result['uid']
        camp = camps_by_uid.get(uid, {})

        enriched = {
            **result,
            'description': camp.get('description', ''),
            'location_string': camp.get('location_string', ''),
            'url': camp.get('url'),
            'images': camp.get('images', [])
        }
        enriched_results.append(enriched)

    return jsonify({
        'success': True,
        'results': enriched_results
    })


@app.route('/api/example/<profile_name>')
def load_example(profile_name):
    """
    Load example user profiles for testing.

    Available profiles:
    - spiritual: Spiritual workshop seeker
    - party: Party animal
    - sober_queer: Sober LGBTQ+ community seeker
    - family: Family with kids
    """
    examples = {
        'spiritual': {
            'name': 'Spiritual Workshop Seeker',
            'profile': {
                'woo_woo': 90,
                'workshops': 85,
                'sound_party': 20,
                'art': 60,
                'description': "I'm looking for a contemplative space with meditation, "
                              "healing workshops, and spiritual practices. I prefer quiet "
                              "environments over loud parties."
            }
        },
        'party': {
            'name': 'Party Animal',
            'profile': {
                'sound_party': 95,
                'hospitality': 80,
                'woo_woo': 10,
                'description': "I want to dance all night at camps with amazing sound systems, "
                              "DJs, and bars. Give me music, beats, and high energy!"
            }
        },
        'sober_queer': {
            'name': 'Sober LGBTQ+ Community Seeker',
            'profile': {
                'sober': 90,
                'queer': 90,
                'workshops': 60,
                'sound_party': 40,
                'description': "I'm a sober queer person looking for affirming spaces "
                              "with recovery support and LGBTQ+ community."
            }
        },
        'family': {
            'name': 'Family with Kids',
            'profile': {
                'family': 95,
                'art': 75,
                'workshops': 60,
                'sound_party': 25,
                'description': "Looking for family-friendly camps with activities for kids, "
                              "art projects, and a welcoming daytime vibe."
            }
        },
        'maker': {
            'name': 'Maker/Engineer',
            'profile': {
                'workshops': 80,
                'art': 70,
                'sound_party': 40,
                'woo_woo': 20,
                'description': "I love hands-on building, learning new technical skills, "
                              "and making art. Looking for maker spaces and workshops."
            }
        },
        'chill': {
            'name': 'Chill Vibes',
            'profile': {
                'music_ambient_chill': 85,
                'hospitality': 70,
                'art': 60,
                'woo_woo': 50,
                'description': "I want a relaxed, welcoming atmosphere. Good conversations, "
                              "tea, and gentle activities. Not into loud parties."
            }
        },
        'jazz_lover': {
            'name': '🎷 Jazz Lover',
            'profile': {
                'music_jazz_blues': 95,
                'music_classical': 70,
                'music_electronic': 10,
                'hospitality': 70,
                'description': "I love jazz, blues, and live improvisation. Looking for sophisticated music camps."
            }
        },
        'techno_raver': {
            'name': '🎧 Techno Raver',
            'profile': {
                'music_electronic': 95,
                'music_bass_sound_systems': 90,
                'music_disco_funk': 60,
                'hospitality': 75,
                'description': "I want to dance all night to techno, house, and bass-heavy electronic music!"
            }
        },
        'latin_dancer': {
            'name': '💃 Latin Dancer',
            'profile': {
                'music_latin': 95,
                'music_disco_funk': 75,
                'hospitality': 70,
                'description': "Salsa, cumbia, reggaeton - I love Latin rhythms and want to dance!"
            }
        },
        'live_music_fan': {
            'name': '🎸 Live Music Fan',
            'profile': {
                'music_live_bands': 90,
                'music_rock': 75,
                'music_jazz_blues': 60,
                'hospitality': 65,
                'description': "I love live performances, jam sessions, and watching musicians create magic."
            }
        },
        'classical_fan': {
            'name': '🎻 Classical Fan',
            'profile': {
                'music_classical': 90,
                'music_ambient_chill': 60,
                'music_electronic': 15,
                'woo_woo': 40,
                'description': "I love orchestras, choirs, and classical chamber music."
            }
        }
    }

    example = examples.get(profile_name)
    if example:
        return jsonify({
            'success': True,
            'example': example
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Example not found'
        }), 404


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("BRC CAMP RECOMMENDATION QUIZ")
    print("=" * 80)
    print("\nStarting web server...")
    print("Open your browser to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 80 + "\n")

    app.run(debug=True, port=5000)
