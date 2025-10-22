#!/usr/bin/env python3
"""
Test keyword-based search
"""

from rank_camps import CampRanker, UserProfile

ranker = CampRanker()

print("\n" + "="*80)
print("TEST: Keyword search for 'breathwork'")
print("="*80)

profile = UserProfile(description="breathwork")
results = ranker.rank(profile, top_k=10)

print("\nTop 10 results:\n")
for camp in results:
    print(f"{camp['rank']}. {camp['name']} (score: {camp['score']:.1f})")
    print(f"   Embedding: {camp['component_scores']['embedding_similarity']:.1f}, "
          f"Axis: {camp['component_scores']['axis_match']:.1f}")
    print(f"   {camp['explanation']}")
    print()

print("\n" + "="*80)
print("TEST: Keyword search for 'cola'")
print("="*80)

profile2 = UserProfile(description="cola")
results2 = ranker.rank(profile2, top_k=10)

print("\nTop 10 results:\n")
for camp in results2:
    print(f"{camp['rank']}. {camp['name']} (score: {camp['score']:.1f})")
    print(f"   Embedding: {camp['component_scores']['embedding_similarity']:.1f}, "
          f"Axis: {camp['component_scores']['axis_match']:.1f}")
    print(f"   {camp['explanation']}")
    print()
