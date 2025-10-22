#!/usr/bin/env python3
"""
Test what happens when user checks Jazz/Blues checkbox
"""

from rank_camps import CampRanker, UserProfile

ranker = CampRanker()

# Test with just Jazz checkbox (value 90)
profile = UserProfile(music_jazz_blues=90)

results = ranker.rank(profile, top_k=10)

print('\nTop 10 results for Jazz/Blues lover (checkbox only, value=90):\n')
for camp in results:
    jazz_score = camp['axes'].get('music_jazz_blues', {}).get('score', 0)
    print(f'{camp["rank"]}. {camp["name"]} (total: {camp["score"]:.1f}, jazz: {jazz_score:.0f})')
    print(f'   {camp["explanation"]}')
    print()
