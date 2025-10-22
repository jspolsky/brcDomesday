#!/usr/bin/env python3
"""
Generate personality-based camp features.

This replaces the old "what do you want" axes with "who are you" personality axes.
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Define personality-based feature axes
PERSONALITY_AXES = {
    # Spectrum 1: Energy Level
    'high_energy_social': {
        'name': 'High Energy Social',
        'keywords': ['party', 'dance', 'dancing', 'dj', 'music', 'loud', 'energetic',
                    'crowd', 'nightclub', 'rave', 'disco', 'club', 'bar', 'drinks',
                    'social', 'meet', 'mingle', 'extrovert', 'outgoing', 'lively'],
        'description': 'Extroverted, high-energy, loves parties and crowds'
    },

    'quiet_contemplative': {
        'name': 'Quiet Contemplative',
        'keywords': ['quiet', 'calm', 'peaceful', 'meditation', 'meditate', 'reflect',
                    'contemplat', 'serene', 'tranquil', 'intimate', 'small group',
                    'introspect', 'mindful', 'zen', 'silence', 'retreat', 'introvert'],
        'description': 'Introverted, calm, reflective, prefers quiet spaces'
    },

    # Spectrum 2: Time of Day
    'night_owl': {
        'name': 'Night Owl',
        'keywords': ['night', 'midnight', 'late', 'dawn', 'sunrise', '2am', '3am',
                    'all night', 'nocturnal', 'after dark', 'evening', 'sunset',
                    'late night', 'nighttime'],
        'description': 'Most alive at night, loves late-night adventures'
    },

    'early_bird': {
        'name': 'Early Bird',
        'keywords': ['morning', 'sunrise', 'breakfast', 'dawn', 'early', 'am',
                    'wake', 'coffee', 'first light', 'daybreak', 'brunch', 'yoga',
                    'morning ritual'],
        'description': 'Morning person, loves sunrise and fresh starts'
    },

    # Spectrum 3: Participation Style
    'hands_on_maker': {
        'name': 'Hands-On Maker',
        'keywords': ['build', 'make', 'craft', 'create', 'diy', 'hands-on', 'workshop',
                    'construct', 'fabricate', 'learn', 'teach', 'maker', 'tinker',
                    'hack', 'assemble', 'participate', 'interactive', 'do'],
        'description': 'Loves building, making, and hands-on participation'
    },

    'observer_appreciator': {
        'name': 'Observer Appreciator',
        'keywords': ['watch', 'view', 'see', 'experience', 'observe', 'appreciate',
                    'spectate', 'audience', 'show', 'performance', 'exhibit', 'display',
                    'gallery', 'tour', 'visit', 'witness'],
        'description': 'Enjoys watching, experiencing, and appreciating'
    },

    # Spectrum 4: Intellectual Style
    'deep_thinker': {
        'name': 'Deep Thinker',
        'keywords': ['philosophy', 'intellectual', 'discuss', 'debate', 'conversation',
                    'think', 'deep', 'theory', 'idea', 'concept', 'learn', 'explore',
                    'question', 'academic', 'science', 'lecture', 'talk', 'salon',
                    'discourse'],
        'description': 'Loves deep conversations and intellectual exploration'
    },

    'playful_prankster': {
        'name': 'Playful Prankster',
        'keywords': ['fun', 'silly', 'prank', 'joke', 'humor', 'funny', 'laugh',
                    'ridiculous', 'absurd', 'game', 'play', 'mischief', 'chaos',
                    'shenanigan', 'comedy', 'hilarious', 'goofy', 'weird', 'whimsy'],
        'description': 'Fun-loving, playful, enjoys pranks and silliness'
    },

    # Spectrum 5: Organization
    'structured_organized': {
        'name': 'Structured Organized',
        'keywords': ['schedule', 'organized', 'plan', 'structure', 'systematic',
                    'calendar', 'timetable', 'program', 'agenda', 'curated',
                    'registration', 'sign up', 'reserve', 'booking', 'organized'],
        'description': 'Likes structure, schedules, and organization'
    },

    'spontaneous_chaotic': {
        'name': 'Spontaneous Chaotic',
        'keywords': ['spontaneous', 'random', 'chaos', 'chaotic', 'improvise',
                    'unplanned', 'surprise', 'unexpected', 'anytime', 'drop in',
                    'no schedule', 'freestyle', 'wild', 'unpredictable', 'improv'],
        'description': 'Goes with the flow, loves spontaneity and chaos'
    },

    # Spectrum 6: Mystical vs Rational
    'mystical_spiritual': {
        'name': 'Mystical Spiritual',
        'keywords': ['spirit', 'mystical', 'magic', 'energy', 'cosmic', 'universe',
                    'healing', 'chakra', 'aura', 'ritual', 'ceremony', 'sacred',
                    'divine', 'transcend', 'soul', 'astrology', 'tarot', 'oracle',
                    'goddess', 'enlighten'],
        'description': 'Spiritual, mystical, believes in energy and magic'
    },

    'rational_skeptical': {
        'name': 'Rational Skeptical',
        'keywords': ['science', 'rational', 'logic', 'evidence', 'practical',
                    'engineer', 'tech', 'technology', 'data', 'research', 'experiment',
                    'math', 'physics', 'fact', 'proof', 'skeptic', 'empirical'],
        'description': 'Rational, science-based, values logic and evidence'
    },

    # Spectrum 7: Social Style
    'generous_host': {
        'name': 'Generous Host',
        'keywords': ['hospitality', 'serve', 'give', 'provide', 'host', 'welcome',
                    'food', 'drink', 'meal', 'coffee', 'tea', 'snack', 'gift',
                    'share', 'offer', 'service', 'care', 'nurture', 'feed'],
        'description': 'Loves hosting, serving, and taking care of others'
    },

    'social_butterfly': {
        'name': 'Social Butterfly',
        'keywords': ['meet', 'social', 'network', 'connect', 'community', 'friend',
                    'people', 'gathering', 'mixer', 'mingle', 'conversation',
                    'hang out', 'chill', 'together', 'collective', 'connect'],
        'description': 'Loves meeting new people and socializing'
    },

    # Spectrum 8: Scale Preference
    'intimate_small_scale': {
        'name': 'Intimate Small Scale',
        'keywords': ['small', 'intimate', 'cozy', 'personal', 'one-on-one',
                    'private', 'close', 'few people', 'exclusive', 'limited',
                    'boutique', 'micro', 'tiny', 'nook'],
        'description': 'Prefers small, intimate gatherings'
    },

    'large_scale_spectacle': {
        'name': 'Large Scale Spectacle',
        'keywords': ['big', 'large', 'massive', 'huge', 'spectacular', 'grand',
                    'epic', 'giant', 'enormous', 'vast', 'immense', 'mega',
                    'hundreds', 'thousands', 'crowd', 'scale'],
        'description': 'Loves big crowds and grand spectacles'
    }
}


def compute_keyword_score(text: str, keywords: list) -> int:
    """
    Count keyword matches in text.
    Returns raw count of matches.
    """
    text_lower = text.lower()
    count = 0

    for keyword in keywords:
        # Count occurrences of this keyword
        count += text_lower.count(keyword)

    return count


def main():
    print("="*80)
    print("GENERATING PERSONALITY-BASED CAMP FEATURES")
    print("="*80)

    # Load shaped camp data
    data_path = Path(__file__).parent / 'shaped_camps.json'
    print(f"\nLoading camps from {data_path}...")

    with open(data_path) as f:
        camps = json.load(f)

    print(f"Loaded {len(camps)} camps")

    # Step 1: Generate embeddings
    print("\n" + "-"*80)
    print("STEP 1: Generating embeddings")
    print("-"*80)

    model = SentenceTransformer('all-MiniLM-L6-v2')

    embeddings = []
    for i, camp in enumerate(camps):
        if (i + 1) % 100 == 0:
            print(f"  Encoded {i+1}/{len(camps)} camps...")

        embedding = model.encode(
            camp['text_corpus'],
            normalize_embeddings=True
        )
        embeddings.append(embedding.tolist())

    print(f"  ✓ Generated {len(embeddings)} embeddings (dimension: {len(embeddings[0])})")

    # Step 2: Compute personality axis scores
    print("\n" + "-"*80)
    print("STEP 2: Computing personality axis scores")
    print("-"*80)

    # First pass: compute raw scores
    raw_scores = {axis_key: [] for axis_key in PERSONALITY_AXES.keys()}

    for camp in camps:
        text = camp['text_corpus']

        for axis_key, axis_info in PERSONALITY_AXES.items():
            score = compute_keyword_score(text, axis_info['keywords'])
            raw_scores[axis_key].append(score)

    # Compute percentiles for normalization
    print("\n  Computing percentile normalization...")
    normalized_scores = {}

    for axis_key, scores in raw_scores.items():
        scores_array = np.array(scores)

        # Compute percentiles
        p0 = np.min(scores_array)
        p50 = np.percentile(scores_array, 50)
        p95 = np.percentile(scores_array, 95)

        print(f"  {PERSONALITY_AXES[axis_key]['name']:30s} p0={p0:5.0f} p50={p50:5.0f} p95={p95:5.0f}")

        # Normalize to 0-100 scale
        # 0 = minimum, 50 = median, 100 = 95th percentile
        normalized = []
        for score in scores_array:
            if score <= p50:
                # Map [p0, p50] to [0, 50]
                if p50 > p0:
                    norm = 50 * (score - p0) / (p50 - p0)
                else:
                    norm = 0
            else:
                # Map [p50, p95] to [50, 100]
                if p95 > p50:
                    norm = 50 + 50 * (score - p50) / (p95 - p50)
                else:
                    norm = 50

            # Clamp to [0, 100]
            norm = max(0, min(100, norm))
            normalized.append(norm)

        normalized_scores[axis_key] = normalized

    # Step 3: Build feature records
    print("\n" + "-"*80)
    print("STEP 3: Building feature records")
    print("-"*80)

    features = []

    for i, camp in enumerate(camps):
        feature = {
            'name': camp['name'],
            'uid': camp['uid'],
            'hometown': camp['hometown'],
            'years_active': camp['years_active']['total_years'],
            'event_count': camp['event_count'],
            'embedding': embeddings[i],
            'axes': {}
        }

        # Add all personality axis scores
        for axis_key, axis_info in PERSONALITY_AXES.items():
            feature['axes'][axis_key] = {
                'name': axis_info['name'],
                'score': float(normalized_scores[axis_key][i])
            }

        features.append(feature)

    # Step 4: Save to file
    output_path = Path(__file__).parent / 'camp_personality_features.json'
    print(f"\n  Saving to {output_path}...")

    with open(output_path, 'w') as f:
        json.dump(features, f, indent=2)

    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Saved {len(features)} camp features ({file_size:.1f} MB)")

    # Step 5: Summary statistics
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    print(f"\nGenerated features for {len(features)} camps")
    print(f"Embedding dimensions: {len(embeddings[0])}")
    print(f"Personality axes: {len(PERSONALITY_AXES)}")
    print(f"\nPersonality spectrums:")
    print("  1. High Energy Social ↔️ Quiet Contemplative")
    print("  2. Night Owl ↔️ Early Bird")
    print("  3. Hands-On Maker ↔️ Observer Appreciator")
    print("  4. Deep Thinker ↔️ Playful Prankster")
    print("  5. Structured Organized ↔️ Spontaneous Chaotic")
    print("  6. Mystical Spiritual ↔️ Rational Skeptical")
    print("  7. Generous Host ↔️ Social Butterfly")
    print("  8. Intimate Small Scale ↔️ Large Scale Spectacle")

    print("\n" + "="*80)
    print("✓ PERSONALITY FEATURES GENERATED!")
    print("="*80)


if __name__ == '__main__':
    main()
