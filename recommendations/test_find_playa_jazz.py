#!/usr/bin/env python3
"""
Find Playa Jazz Cafe in the rankings
"""

from rank_camps import CampRanker, UserProfile

ranker = CampRanker()

# Test with just Jazz checkbox (value 90)
profile = UserProfile(music_jazz_blues=90)

results = ranker.rank(profile, top_k=50)

# Find Playa Jazz Cafe
for camp in results:
    if 'jazz' in camp['name'].lower() and 'cafe' in camp['name'].lower():
        jazz_score = camp['axes'].get('music_jazz_blues', {}).get('score', 0)
        print(f'\nFound: {camp["name"]}')
        print(f'Rank: {camp["rank"]}')
        print(f'Total score: {camp["score"]:.1f}')
        print(f'Jazz/Blues score: {jazz_score:.0f}')
        print(f'Component scores: {camp["component_scores"]}')
        print(f'Explanation: {camp["explanation"]}')
        break
else:
    print("\nPlaya Jazz Cafe not found in top 50!")
    print("\nSearching all camps...")

    # Search in camp features directly
    for camp in ranker.camps:
        if 'jazz' in camp['name'].lower() and 'cafe' in camp['name'].lower():
            print(f'\nFound in features: {camp["name"]}')
            print(f'Jazz score in features: {camp["axes"].get("music_jazz_blues", {}).get("score", 0):.0f}')
            break
