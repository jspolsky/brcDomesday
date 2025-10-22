#!/usr/bin/env python3
"""
Explore personality-based axes for camp matching.

Instead of "what do you want" (jazz, sober, workshops), we're looking for
"who are you" (night owl, prankster, organized, social butterfly)
"""

import json
from pathlib import Path
from collections import defaultdict

# Load shaped camp data
data_path = Path(__file__).parent / 'shaped_camps.json'
print(f"Loading shaped camps from {data_path}...")

with open(data_path) as f:
    camps = json.load(f)

print(f"Loaded {len(camps)} camps\n")

# Define personality axes with keywords
personality_axes = {
    # Energy & Social Style
    'high_energy_social': {
        'name': 'High Energy Social',
        'description': 'Extroverted, party, dancing, loud, energetic, crowd',
        'keywords': ['party', 'dance', 'dancing', 'dj', 'music', 'loud', 'energetic',
                    'crowd', 'nightclub', 'rave', 'disco', 'club', 'bar', 'drinks',
                    'social', 'meet', 'mingle', 'extrovert']
    },

    'quiet_contemplative': {
        'name': 'Quiet Contemplative',
        'description': 'Introverted, calm, peaceful, meditation, reflection',
        'keywords': ['quiet', 'calm', 'peaceful', 'meditation', 'meditate', 'reflect',
                    'contemplat', 'serene', 'tranquil', 'intimate', 'small group',
                    'introspect', 'mindful', 'zen', 'silence', 'retreat']
    },

    # Time of Day
    'night_owl': {
        'name': 'Night Owl',
        'description': 'Late night, midnight, all night, dawn, nocturnal',
        'keywords': ['night', 'midnight', 'late', 'dawn', 'sunrise', '2am', '3am',
                    'all night', 'nocturnal', 'after dark', 'evening', 'sunset']
    },

    'early_bird': {
        'name': 'Early Bird',
        'description': 'Morning, sunrise, breakfast, dawn, early',
        'keywords': ['morning', 'sunrise', 'breakfast', 'dawn', 'early', 'am',
                    'wake', 'coffee', 'first light', 'daybreak', 'brunch']
    },

    # Participation Style
    'hands_on_maker': {
        'name': 'Hands-On Maker',
        'description': 'DIY, build, create, make, craft, workshop, participate',
        'keywords': ['build', 'make', 'craft', 'create', 'diy', 'hands-on', 'workshop',
                    'construct', 'fabricate', 'learn', 'teach', 'build', 'maker',
                    'tinker', 'hack', 'assemble', 'participate', 'interactive']
    },

    'observer_appreciator': {
        'name': 'Observer/Appreciator',
        'description': 'Watch, view, experience, appreciate, spectator, audience',
        'keywords': ['watch', 'view', 'see', 'experience', 'observe', 'appreciate',
                    'spectate', 'audience', 'show', 'performance', 'exhibit', 'display',
                    'gallery', 'tour', 'visit']
    },

    # Intellectual Style
    'deep_thinker': {
        'name': 'Deep Thinker',
        'description': 'Philosophy, intellectual, discuss, debate, conversation',
        'keywords': ['philosophy', 'intellectual', 'discuss', 'debate', 'conversation',
                    'think', 'deep', 'theory', 'idea', 'concept', 'learn', 'explore',
                    'question', 'academic', 'science', 'lecture', 'talk', 'salon']
    },

    'playful_prankster': {
        'name': 'Playful Prankster',
        'description': 'Fun, silly, pranks, games, humor, jokes, ridiculous',
        'keywords': ['fun', 'silly', 'prank', 'joke', 'humor', 'funny', 'laugh',
                    'ridiculous', 'absurd', 'game', 'play', 'mischief', 'chaos',
                    'shenanigan', 'comedy', 'hilarious', 'goofy', 'weird']
    },

    # Organization Style
    'structured_organized': {
        'name': 'Structured & Organized',
        'description': 'Schedule, organized, plan, structure, systematic',
        'keywords': ['schedule', 'organized', 'plan', 'structure', 'systematic',
                    'calendar', 'timetable', 'program', 'agenda', 'curated',
                    'registration', 'sign up', 'reserve', 'booking']
    },

    'spontaneous_chaotic': {
        'name': 'Spontaneous & Chaotic',
        'description': 'Spontaneous, random, chaotic, improvise, unplanned',
        'keywords': ['spontaneous', 'random', 'chaos', 'chaotic', 'improvise',
                    'unplanned', 'surprise', 'unexpected', 'anytime', 'drop in',
                    'no schedule', 'freestyle', 'wild', 'unpredictable']
    },

    # Mystical vs Rational
    'mystical_spiritual': {
        'name': 'Mystical & Spiritual',
        'description': 'Spirituality, mystical, magic, energy, cosmic',
        'keywords': ['spirit', 'mystical', 'magic', 'energy', 'cosmic', 'universe',
                    'healing', 'chakra', 'aura', 'ritual', 'ceremony', 'sacred',
                    'divine', 'transcend', 'soul', 'astrology', 'tarot', 'oracle']
    },

    'rational_skeptical': {
        'name': 'Rational & Skeptical',
        'description': 'Science, rational, logic, evidence, practical',
        'keywords': ['science', 'rational', 'logic', 'evidence', 'practical',
                    'engineer', 'tech', 'technology', 'data', 'research', 'experiment',
                    'math', 'physics', 'fact', 'proof', 'skeptic']
    },

    # Social Connection Style
    'generous_host': {
        'name': 'Generous Host',
        'description': 'Hospitality, serve, give, provide, host, welcome',
        'keywords': ['hospitality', 'serve', 'give', 'provide', 'host', 'welcome',
                    'food', 'drink', 'meal', 'coffee', 'tea', 'snack', 'gift',
                    'share', 'offer', 'service', 'care', 'nurture']
    },

    'social_butterfly': {
        'name': 'Social Butterfly',
        'description': 'Meet people, socialize, network, connect, community',
        'keywords': ['meet', 'social', 'network', 'connect', 'community', 'friend',
                    'people', 'gathering', 'mixer', 'mingle', 'conversation',
                    'hang out', 'chill', 'together', 'collective']
    },

    # Scale Preference
    'intimate_small_scale': {
        'name': 'Intimate & Small Scale',
        'description': 'Small, intimate, cozy, personal, one-on-one',
        'keywords': ['small', 'intimate', 'cozy', 'personal', 'one-on-one',
                    'private', 'close', 'few people', 'exclusive', 'limited',
                    'boutique', 'micro', 'tiny']
    },

    'large_scale_spectacle': {
        'name': 'Large Scale Spectacle',
        'description': 'Big, massive, huge, spectacular, grand, epic',
        'keywords': ['big', 'large', 'massive', 'huge', 'spectacular', 'grand',
                    'epic', 'giant', 'enormous', 'vast', 'immense', 'mega',
                    'hundreds', 'thousands', 'crowd']
    }
}

print("="*80)
print("PERSONALITY AXIS ANALYSIS")
print("="*80)

results = {}

for axis_key, axis_info in personality_axes.items():
    print(f"\n{axis_info['name']}")
    print(f"  Keywords: {', '.join(axis_info['keywords'][:10])}...")

    # Count camps that mention these keywords
    matching_camps = []

    for camp in camps:
        text = camp['text_corpus'].lower()

        # Count keyword matches
        matches = sum(1 for keyword in axis_info['keywords'] if keyword in text)

        if matches > 0:
            matching_camps.append({
                'name': camp['name'],
                'matches': matches,
                'text_length': len(text)
            })

    # Sort by number of matches
    matching_camps.sort(key=lambda x: x['matches'], reverse=True)

    prevalence = len(matching_camps) / len(camps) * 100

    print(f"  Prevalence: {prevalence:.1f}% ({len(matching_camps)} camps)")

    if matching_camps:
        print(f"  Top camp: {matching_camps[0]['name']} ({matching_camps[0]['matches']} keyword matches)")

    results[axis_key] = {
        'name': axis_info['name'],
        'prevalence': prevalence,
        'count': len(matching_camps),
        'top_camp': matching_camps[0]['name'] if matching_camps else None
    }

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

# Sort by prevalence
sorted_axes = sorted(results.items(), key=lambda x: x[1]['prevalence'], reverse=True)

for axis_key, stats in sorted_axes:
    print(f"{stats['name']:30s} {stats['prevalence']:5.1f}% ({stats['count']:4d} camps)")

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

print("\nViable axes (>10% prevalence):")
for axis_key, stats in sorted_axes:
    if stats['prevalence'] > 10:
        print(f"  ✓ {stats['name']}")

print("\nMarginal axes (5-10% prevalence):")
for axis_key, stats in sorted_axes:
    if 5 <= stats['prevalence'] <= 10:
        print(f"  ~ {stats['name']}")

print("\nLow signal axes (<5% prevalence):")
for axis_key, stats in sorted_axes:
    if stats['prevalence'] < 5:
        print(f"  ✗ {stats['name']}")
