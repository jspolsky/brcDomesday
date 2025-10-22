#!/usr/bin/env python3
"""
Feature Generation for BRC Camp Recommendation Engine

Generates:
1. Vector embeddings using sentence-transformers
2. Scalar feature scores for the 8 core axes

Input: shaped_camps.json
Output: camp_features.json (embeddings + axis scores)
"""

import json
import re
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

print("Loading libraries (this may take a moment)...")
from sentence_transformers import SentenceTransformer


# Define feature axes with their keyword sets
# Now with 10 music genre axes + 7 other axes = 17 total
FEATURE_AXES = {
    # === MUSIC GENRES (10 axes) ===
    'music_electronic': {
        'name': 'Electronic Dance Music',
        'keywords': [
            'techno', 'house', 'house music', 'deep house', 'tech house',
            'trance', 'psytrance', 'progressive', 'edm', 'electronic dance',
            'minimal', 'detroit techno', 'acid house', 'drum and bass', 'dnb',
            'dubstep', 'bass music', 'electro'
        ],
        'description': 'Techno, house, trance, EDM - high energy electronic'
    },
    'music_disco_funk': {
        'name': 'Disco/Funk/Soul',
        'keywords': [
            'disco', 'funk', 'funky', 'soul', 'motown', 'boogie',
            'nu-disco', 'disco ball', 'groove', 'r&b'
        ],
        'description': 'Groovy, danceable, feel-good vibes'
    },
    'music_ambient_chill': {
        'name': 'Ambient/Chill/Downtempo',
        'keywords': [
            'ambient', 'chill', 'downtempo', 'chillout', 'lounge',
            'soundscape', 'atmospheric', 'relaxing music', 'meditation music',
            'ethereal', 'drone'
        ],
        'description': 'Relaxing soundscapes, lounge, chill vibes'
    },
    'music_live_bands': {
        'name': 'Live Music/Bands',
        'keywords': [
            'live music', 'live band', 'live performance', 'musician',
            'musicians', 'band', 'bands', 'jam', 'jamming', 'jam session',
            'acoustic', 'singer', 'vocalist'
        ],
        'description': 'Live performances, jam sessions, acoustic'
    },
    'music_rock': {
        'name': 'Rock/Punk/Alternative',
        'keywords': [
            'rock', 'punk', 'alternative', 'indie', 'grunge', 'metal',
            'hard rock', 'punk rock', 'garage', 'guitar', 'guitars'
        ],
        'description': 'Rock, punk, metal, alternative music'
    },
    'music_hiphop': {
        'name': 'Hip Hop/Rap/Beats',
        'keywords': [
            'hip hop', 'hiphop', 'rap', 'mc', 'beats', 'beat maker',
            'turntable', 'turntables', 'scratch', 'breakbeat', 'boom bap'
        ],
        'description': 'Hip hop, rap, beat culture'
    },
    'music_latin': {
        'name': 'Latin Music',
        'keywords': [
            'salsa', 'cumbia', 'latin', 'reggaeton', 'bachata',
            'merengue', 'latin music', 'latino', 'latina'
        ],
        'description': 'Salsa, cumbia, reggaeton, Latin beats'
    },
    'music_world_tribal': {
        'name': 'World/Tribal/Ethnic',
        'keywords': [
            'world music', 'tribal', 'african', 'reggae', 'afrobeat',
            'brazilian', 'samba', 'indigenous', 'ethnic', 'folk',
            'traditional music', 'didgeridoo', 'drums', 'drumming'
        ],
        'description': 'World music, tribal, reggae, folk traditions'
    },
    'music_jazz_blues': {
        'name': 'Jazz/Blues',
        'keywords': [
            'jazz', 'blues', 'swing', 'bebop', 'improvisation',
            'big band', 'saxophone', 'trumpet', 'piano bar'
        ],
        'description': 'Jazz, blues, swing, improvisation'
    },
    'music_classical': {
        'name': 'Classical/Orchestra',
        'keywords': [
            'classical', 'orchestra', 'symphony', 'choir', 'choral',
            'opera', 'string quartet', 'chamber music', 'violin',
            'cello', 'orchestral', 'classical music', 'baroque', 'concerto'
        ],
        'description': 'Classical music, orchestras, choirs, opera'
    },
    'music_bass_sound_systems': {
        'name': 'Bass/Sound Systems',
        'keywords': [
            'sound system', 'soundsystem', 'bass', 'bassline', 'subwoofer',
            'speakers', 'amplified', 'heavy bass', 'bass heavy', 'bass music'
        ],
        'description': 'Heavy bass, sound systems, bass culture'
    },

    # === NON-MUSIC AXES (7 axes) ===
    'hospitality': {
        'name': 'Food/Hospitality',
        'keywords': [
            'bar', 'drinks', 'coffee', 'tea', 'food', 'kitchen', 'meal',
            'breakfast', 'brunch', 'dinner', 'feast', 'restaurant', 'cafe',
            'beverage', 'cocktail', 'mocktail', 'beer', 'wine', 'snacks'
        ],
        'description': 'Food and beverage hospitality focus'
    },
    'workshops': {
        'name': 'Workshops/Learning',
        'keywords': [
            'workshop', 'class', 'learn', 'teach', 'lecture', 'seminar',
            'talk', 'panel', 'discussion', 'education', 'skill', 'training',
            'instruction', 'course', 'lesson', 'tutorial'
        ],
        'description': 'Educational and learning-oriented activities'
    },
    'woo_woo': {
        'name': 'Woo-woo/Spirituality',
        'keywords': [
            'chakra', 'chakras', 'energy healing', 'reiki', 'astrology', 'oracle',
            'breathwork', 'tantra', 'shamanic', 'sound bath', 'meditation',
            'spiritual', 'healing', 'crystal', 'tarot', 'goddess', 'divine',
            'sacred', 'ceremony', 'ritual', 'psychic', 'intuitive'
        ],
        'description': 'Spiritual and new-age practices vs secular'
    },
    'art': {
        'name': 'Art Focus',
        'keywords': [
            'art', 'artist', 'paint', 'painting', 'sculpture', 'gallery', 'creative',
            'drawing', 'installation', 'performance art', 'mural', 'craft',
            'artistic', 'create', 'creation', 'visual', 'exhibit'
        ],
        'description': 'Art-making and creative expression'
    },
    'queer': {
        'name': 'LGBTQ+/Queer',
        'keywords': [
            'queer', 'lgbtq', 'gay', 'lesbian', 'trans', 'transgender',
            'drag', 'pride', 'rainbow', 'bi', 'bisexual', 'nonbinary',
            'non-binary', 'genderqueer', 'pansexual'
        ],
        'description': 'LGBTQ+ centered spaces and events'
    },
    'sober': {
        'name': 'Sober-friendly',
        'keywords': [
            'sober', 'sobriety', 'recovery', 'alcohol-free', 'substance-free',
            'clean', 'non-alcoholic', 'twelve step', '12 step', 'aa', 'na'
        ],
        'description': 'Sober and recovery-oriented spaces'
    },
    'family': {
        'name': 'Family/Kids',
        'keywords': [
            'family', 'kids', 'children', 'child', 'parent', 'toddler',
            'family-friendly', 'all ages', 'kid-friendly', 'youth', 'baby'
        ],
        'description': 'Family and child-friendly activities'
    }
}


def load_shaped_data():
    """Load shaped camp data"""
    data_path = Path(__file__).parent / 'shaped_camps.json'
    with open(data_path) as f:
        return json.load(f)


def count_keywords(text: str, keywords: List[str]) -> int:
    """Count keyword occurrences in text (case-insensitive, word boundaries)"""
    if not text:
        return 0

    text_lower = text.lower()
    total_count = 0

    for keyword in keywords:
        # Use word boundaries for better matching
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        matches = re.findall(pattern, text_lower)
        total_count += len(matches)

    return total_count


def compute_axis_score(camp: Dict, axis_key: str) -> Dict[str, Any]:
    """
    Compute score for a single axis.

    Returns dict with:
    - raw_count: total keyword matches
    - normalized_score: 0-100 score normalized by text length
    - density: matches per 1000 characters
    """
    axis = FEATURE_AXES[axis_key]
    keywords = axis['keywords']

    # Use the full text corpus for scoring
    text = camp.get('text_corpus', '')
    text_length = len(text)

    if text_length == 0:
        return {
            'raw_count': 0,
            'normalized_score': 0,
            'density': 0
        }

    raw_count = count_keywords(text, keywords)

    # Calculate density (matches per 1000 chars)
    density = (raw_count / text_length) * 1000

    # Normalized score will be computed after we see the distribution
    return {
        'raw_count': raw_count,
        'density': density,
        'text_length': text_length
    }


def normalize_axis_scores(all_scores: List[Dict], axis_key: str) -> List[Dict]:
    """
    Normalize scores to 0-100 scale based on distribution.

    Uses percentile-based normalization:
    - 0 = no matches
    - 50 = median density
    - 100 = 95th percentile or above
    """
    # Extract densities for camps with non-zero counts
    densities = [score['axes'][axis_key]['density']
                 for score in all_scores
                 if score['axes'][axis_key]['density'] > 0]

    if not densities:
        # No camps have this axis - all scores stay at 0
        return all_scores

    # Calculate percentiles
    p50 = np.percentile(densities, 50)  # Median
    p95 = np.percentile(densities, 95)  # 95th percentile

    # Normalize each score
    for score in all_scores:
        axis_data = score['axes'][axis_key]
        density = axis_data['density']

        if density == 0:
            normalized = 0
        elif density >= p95:
            normalized = 100
        elif density >= p50:
            # Scale 50-100 for above median
            normalized = 50 + ((density - p50) / (p95 - p50)) * 50
        else:
            # Scale 0-50 for below median
            normalized = (density / p50) * 50

        axis_data['normalized_score'] = round(normalized, 1)

    return all_scores


def generate_embeddings(camps: List[Dict], model_name: str = 'all-MiniLM-L6-v2'):
    """
    Generate embeddings for all camps using sentence-transformers.

    Model: all-MiniLM-L6-v2 (384 dimensions, fast, good quality)
    """
    print(f"\nLoading embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    print(f"Generating embeddings for {len(camps)} camps...")

    # Extract text corpora
    texts = [camp.get('text_corpus', '') for camp in camps]

    # Generate embeddings (with progress bar)
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=32,
        normalize_embeddings=True  # Normalize for cosine similarity
    )

    print(f"Generated embeddings: shape {embeddings.shape}")

    return embeddings


def compute_all_features(camps: List[Dict]) -> List[Dict]:
    """Compute all features for all camps"""

    print("\n" + "=" * 80)
    print("COMPUTING FEATURE SCORES")
    print("=" * 80)

    # First pass: compute raw scores for all axes
    all_scores = []

    for camp in camps:
        camp_scores = {
            'uid': camp['uid'],
            'name': camp['name'],
            'axes': {}
        }

        for axis_key in FEATURE_AXES.keys():
            camp_scores['axes'][axis_key] = compute_axis_score(camp, axis_key)

        all_scores.append(camp_scores)

    # Second pass: normalize scores based on distribution
    print("\nNormalizing scores...")
    for axis_key in FEATURE_AXES.keys():
        all_scores = normalize_axis_scores(all_scores, axis_key)

    return all_scores


def print_axis_statistics(all_scores: List[Dict]):
    """Print statistics about each axis"""
    print("\n" + "=" * 80)
    print("AXIS STATISTICS")
    print("=" * 80)

    for axis_key, axis_info in FEATURE_AXES.items():
        print(f"\n{axis_info['name']} ({axis_key}):")
        print(f"  {axis_info['description']}")

        # Count camps with non-zero scores
        scores = [s['axes'][axis_key]['normalized_score'] for s in all_scores]
        non_zero = sum(1 for s in scores if s > 0)

        print(f"  Camps with signal: {non_zero}/{len(all_scores)} ({non_zero/len(all_scores)*100:.1f}%)")

        if non_zero > 0:
            non_zero_scores = [s for s in scores if s > 0]
            print(f"  Score range: {min(scores):.1f} - {max(scores):.1f}")
            print(f"  Mean score (non-zero): {np.mean(non_zero_scores):.1f}")
            print(f"  Median score (non-zero): {np.median(non_zero_scores):.1f}")

        # Show top 3 camps
        sorted_camps = sorted(all_scores,
                             key=lambda x: x['axes'][axis_key]['normalized_score'],
                             reverse=True)
        print(f"  Top 3 camps:")
        for i, camp in enumerate(sorted_camps[:3], 1):
            score = camp['axes'][axis_key]['normalized_score']
            count = camp['axes'][axis_key]['raw_count']
            print(f"    {i}. {camp['name']}: score={score:.1f}, matches={count}")


def save_features(camps: List[Dict], embeddings: np.ndarray, scores: List[Dict], output_path: Path):
    """
    Save embeddings and feature scores to file.

    Format: JSON with embeddings as lists of floats
    """

    # Combine everything
    features = []

    for i, camp in enumerate(camps):
        feature_record = {
            # Identity
            'uid': camp['uid'],
            'name': camp['name'],
            'hometown': camp['hometown'],

            # Embedding (as list for JSON serialization)
            'embedding': embeddings[i].tolist(),

            # Axis scores (just the normalized scores for simplicity)
            'axes': {
                axis_key: {
                    'score': scores[i]['axes'][axis_key]['normalized_score'],
                    'raw_count': scores[i]['axes'][axis_key]['raw_count']
                }
                for axis_key in FEATURE_AXES.keys()
            },

            # Metadata
            'has_description': camp['has_description'],
            'has_events': camp['has_events'],
            'event_count': camp['event_count'],
            'years_active': camp['years_active']['total_years']
        }

        features.append(feature_record)

    with open(output_path, 'w') as f:
        json.dump(features, f, indent=2)

    print(f"\nSaved features for {len(features)} camps to {output_path}")


def show_sample_features(features_data: List[Dict], camp_name: str = None):
    """Show sample feature record"""
    print("\n" + "=" * 80)
    print("SAMPLE FEATURE RECORD")
    print("=" * 80)

    if camp_name:
        sample = next((f for f in features_data if f['name'] == camp_name), None)
    else:
        # Pick a camp with high variance across axes
        sample = features_data[0]

    if not sample:
        print("Camp not found!")
        return

    print(f"\nCamp: {sample['name']}")
    print(f"Hometown: {sample['hometown']}")
    print(f"Years active: {sample['years_active']}")
    print(f"Events: {sample['event_count']}")
    print(f"\nEmbedding: {len(sample['embedding'])} dimensions")
    print(f"  First 5 values: {sample['embedding'][:5]}")
    print(f"\nAxis Scores (0-100):")

    # Sort by score descending
    sorted_axes = sorted(sample['axes'].items(),
                        key=lambda x: x[1]['score'],
                        reverse=True)

    for axis_key, axis_data in sorted_axes:
        axis_name = FEATURE_AXES[axis_key]['name']
        score = axis_data['score']
        count = axis_data['raw_count']

        # Visual bar
        bar_length = int(score / 5)  # 20 chars = 100
        bar = '█' * bar_length

        print(f"  {axis_name:25} {score:5.1f}  {bar}  ({count} matches)")


def main():
    print("\nBRC CAMP FEATURE GENERATION")
    print("=" * 80)
    print()

    # Load shaped data
    print("Loading shaped camp data...")
    camps = load_shaped_data()
    print(f"Loaded {len(camps)} camps")

    # Compute axis scores
    axis_scores = compute_all_features(camps)
    print_axis_statistics(axis_scores)

    # Generate embeddings
    embeddings = generate_embeddings(camps)

    # Create combined feature records
    output_path = Path(__file__).parent / 'camp_features.json'

    # Reload to create features (reusing camps data)
    print("\n" + "=" * 80)
    print("CREATING FEATURE RECORDS")
    print("=" * 80)

    features_data = []
    for i, camp in enumerate(camps):
        feature_record = {
            'uid': camp['uid'],
            'name': camp['name'],
            'hometown': camp['hometown'],
            'embedding': embeddings[i].tolist(),
            'axes': {
                axis_key: {
                    'score': axis_scores[i]['axes'][axis_key]['normalized_score'],
                    'raw_count': axis_scores[i]['axes'][axis_key]['raw_count']
                }
                for axis_key in FEATURE_AXES.keys()
            },
            'has_description': camp['has_description'],
            'has_events': camp['has_events'],
            'event_count': camp['event_count'],
            'years_active': camp['years_active']['total_years']
        }
        features_data.append(feature_record)

    # Save
    with open(output_path, 'w') as f:
        json.dump(features_data, f, indent=2)

    print(f"\nSaved features for {len(features_data)} camps")

    # Show sample
    show_sample_features(features_data)

    print("\n" + "=" * 80)
    print("FEATURE GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nOutput: {output_path}")
    print(f"  - {len(features_data)} camps")
    print(f"  - {len(embeddings[0])} dimensional embeddings")
    print(f"  - {len(FEATURE_AXES)} feature axes")
    print("\nReady for ranking algorithm and quiz interface!")
    print()


if __name__ == '__main__':
    main()
