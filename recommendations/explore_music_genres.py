#!/usr/bin/env python3
"""
Music Genre Exploration for BRC Camps

Analyzes camp descriptions and events to identify different music genres
and create more nuanced music-related axes.
"""

import json
import re
from pathlib import Path
from collections import Counter


def load_shaped_data():
    """Load shaped camp data"""
    data_path = Path(__file__).parent / 'shaped_camps.json'
    with open(data_path) as f:
        return json.load(f)


def count_keywords(text: str, keywords: list) -> dict:
    """Count keyword occurrences in text"""
    if not text:
        return {}

    text_lower = text.lower()
    counts = {}

    for keyword in keywords:
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        matches = re.findall(pattern, text_lower)
        if matches:
            counts[keyword] = len(matches)

    return counts


def analyze_music_genres():
    """Analyze different music genres mentioned in camp data"""

    print("\n" + "=" * 80)
    print("MUSIC GENRE ANALYSIS")
    print("=" * 80)

    camps = load_shaped_data()

    # Define genre keyword sets
    genre_keywords = {
        'Electronic Dance (Techno/House)': [
            'techno', 'house', 'house music', 'deep house', 'tech house',
            'trance', 'psytrance', 'progressive', 'edm', 'electronic dance',
            'minimal', 'detroit techno', 'acid house', 'drum and bass', 'dnb',
            'dubstep', 'bass music', 'electro'
        ],
        'Disco/Funk/Soul': [
            'disco', 'funk', 'funky', 'soul', 'motown', 'boogie',
            'nu-disco', 'disco ball', 'groove', 'r&b'
        ],
        'Ambient/Chill/Downtempo': [
            'ambient', 'chill', 'downtempo', 'chillout', 'lounge',
            'soundscape', 'atmospheric', 'relaxing music', 'meditation music',
            'sound healing', 'sound bath', 'drone', 'ethereal'
        ],
        'Live Music/Bands': [
            'live music', 'live band', 'live performance', 'musician',
            'musicians', 'band', 'bands', 'jam', 'jamming', 'jam session',
            'acoustic', 'singer', 'vocalist'
        ],
        'Rock/Punk/Alternative': [
            'rock', 'punk', 'alternative', 'indie', 'grunge', 'metal',
            'hard rock', 'punk rock', 'garage', 'guitar', 'guitars'
        ],
        'Hip Hop/Rap/Beats': [
            'hip hop', 'hiphop', 'rap', 'mc', 'beats', 'beat maker',
            'turntable', 'turntables', 'scratch', 'breakbeat', 'boom bap'
        ],
        'World/Tribal/Ethnic': [
            'world music', 'tribal', 'african', 'latin', 'reggae',
            'cumbia', 'salsa', 'afrobeat', 'brazilian', 'samba',
            'indigenous', 'ethnic', 'folk', 'traditional music'
        ],
        'Jazz/Blues': [
            'jazz', 'blues', 'swing', 'bebop', 'improvisation',
            'big band', 'saxophone', 'trumpet', 'piano bar'
        ],
        'Experimental/Noise/Avant-garde': [
            'experimental', 'noise', 'avant-garde', 'sound art',
            'abstract', 'unconventional', 'weird music', 'outsider'
        ],
        'DJ Culture': [
            'dj', 'djs', 'deejay', 'disc jockey', 'turntablist',
            'mixing', 'remix', 'vinyl', 'decks', 'cdj'
        ],
        'Sound Systems/Bass Culture': [
            'sound system', 'soundsystem', 'bass', 'bassline', 'subwoofer',
            'speakers', 'amplified', 'loud', 'heavy bass', 'bass heavy'
        ]
    }

    # Analyze each genre
    genre_stats = {}

    for genre_name, keywords in genre_keywords.items():
        matching_camps = []
        total_mentions = 0
        keyword_counts = Counter()

        for camp in camps:
            text = camp['text_corpus']
            matches = count_keywords(text, keywords)

            if matches:
                matching_camps.append({
                    'name': camp['name'],
                    'matches': matches,
                    'total': sum(matches.values())
                })
                total_mentions += sum(matches.values())
                keyword_counts.update(matches)

        genre_stats[genre_name] = {
            'camp_count': len(matching_camps),
            'total_mentions': total_mentions,
            'top_keywords': keyword_counts.most_common(10),
            'top_camps': sorted(matching_camps, key=lambda x: x['total'], reverse=True)[:10]
        }

    # Print results
    print("\nGenre Analysis (sorted by number of camps):\n")

    sorted_genres = sorted(genre_stats.items(), key=lambda x: x[1]['camp_count'], reverse=True)

    for genre_name, stats in sorted_genres:
        pct = stats['camp_count'] / len(camps) * 100
        print(f"{genre_name}:")
        print(f"  Camps: {stats['camp_count']}/{len(camps)} ({pct:.1f}%)")
        print(f"  Total mentions: {stats['total_mentions']}")

        if stats['top_keywords']:
            print(f"  Top keywords: {', '.join(f'{kw} ({cnt})' for kw, cnt in stats['top_keywords'][:5])}")

        if stats['top_camps']:
            print(f"  Top camps:")
            for i, camp in enumerate(stats['top_camps'][:3], 1):
                keyword_str = ', '.join(f"{k}:{v}" for k, v in sorted(camp['matches'].items(),
                                                                        key=lambda x: x[1],
                                                                        reverse=True)[:3])
                print(f"    {i}. {camp['name']} ({camp['total']} mentions: {keyword_str})")

        print()

    # Look for camps with multiple genres
    print("\n" + "=" * 80)
    print("MULTI-GENRE CAMPS")
    print("=" * 80)
    print("\nCamps that mention multiple music genres:\n")

    multi_genre_camps = []
    for camp in camps:
        text = camp['text_corpus']
        genres_found = []

        for genre_name, keywords in genre_keywords.items():
            matches = count_keywords(text, keywords)
            if matches:
                genres_found.append((genre_name, sum(matches.values())))

        if len(genres_found) >= 3:
            multi_genre_camps.append({
                'name': camp['name'],
                'genres': genres_found
            })

    # Sort by number of genres
    multi_genre_camps.sort(key=lambda x: len(x['genres']), reverse=True)

    for camp in multi_genre_camps[:20]:
        print(f"{camp['name']}:")
        for genre, count in sorted(camp['genres'], key=lambda x: x[1], reverse=True):
            print(f"  - {genre}: {count} mentions")
        print()

    # Suggest axis groupings
    print("\n" + "=" * 80)
    print("SUGGESTED MUSIC AXES FOR QUIZ")
    print("=" * 80)
    print()

    suggestions = [
        {
            'axis_name': 'Electronic Dance Music',
            'description': 'Techno, house, trance, EDM - high energy electronic',
            'camps': genre_stats['Electronic Dance (Techno/House)']['camp_count']
        },
        {
            'axis_name': 'Live Bands & Musicians',
            'description': 'Live performances, acoustic, jam sessions',
            'camps': genre_stats['Live Music/Bands']['camp_count']
        },
        {
            'axis_name': 'Chill/Ambient/Downtempo',
            'description': 'Relaxing soundscapes, meditation music, lounge',
            'camps': genre_stats['Ambient/Chill/Downtempo']['camp_count']
        },
        {
            'axis_name': 'Bass/Sound System Culture',
            'description': 'Heavy bass, sound systems, speaker culture',
            'camps': genre_stats['Sound Systems/Bass Culture']['camp_count']
        },
        {
            'axis_name': 'Disco/Funk/Soul',
            'description': 'Groovy, danceable, feel-good vibes',
            'camps': genre_stats['Disco/Funk/Soul']['camp_count']
        }
    ]

    for suggestion in suggestions:
        pct = suggestion['camps'] / len(camps) * 100
        print(f"{suggestion['axis_name']}: {suggestion['camps']} camps ({pct:.1f}%)")
        print(f"  {suggestion['description']}")
        print()

    print("\nRecommendation: Replace generic 'Sound/Party' axis with these more specific axes")
    print("Users can select multiple music genres they're interested in!")


if __name__ == '__main__':
    analyze_music_genres()
