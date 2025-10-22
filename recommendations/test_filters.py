#!/usr/bin/env python3
"""
Test hard filtering for critical axes (queer, sober, family)
"""

from rank_camps import CampRanker, UserProfile

ranker = CampRanker()

print("\n" + "="*80)
print("TEST 1: Sober filter only")
print("="*80)

profile1 = UserProfile(sober=90)
results1 = ranker.rank(profile1, top_k=10)

print(f"\nFound {len(results1)} camps\n")
if results1:
    for camp in results1[:5]:
        sober_score = camp['axes'].get('sober', {}).get('score', 0)
        print(f"{camp['rank']}. {camp['name']} (sober: {sober_score:.0f})")

print("\n" + "="*80)
print("TEST 2: LGBTQ+ filter only")
print("="*80)

profile2 = UserProfile(queer=90)
results2 = ranker.rank(profile2, top_k=10)

print(f"\nFound {len(results2)} camps\n")
if results2:
    for camp in results2[:5]:
        queer_score = camp['axes'].get('queer', {}).get('score', 0)
        print(f"{camp['rank']}. {camp['name']} (queer: {queer_score:.0f})")

print("\n" + "="*80)
print("TEST 3: Family-friendly filter only")
print("="*80)

profile3 = UserProfile(family=90)
results3 = ranker.rank(profile3, top_k=10)

print(f"\nFound {len(results3)} camps\n")
if results3:
    for camp in results3[:5]:
        family_score = camp['axes'].get('family', {}).get('score', 0)
        print(f"{camp['rank']}. {camp['name']} (family: {family_score:.0f})")

print("\n" + "="*80)
print("TEST 4: ALL THREE FILTERS (should return 0 or very few results)")
print("="*80)

profile4 = UserProfile(sober=90, queer=90, family=90)
results4 = ranker.rank(profile4, top_k=10)

print(f"\nFound {len(results4)} camps\n")
if results4:
    for camp in results4:
        sober_score = camp['axes'].get('sober', {}).get('score', 0)
        queer_score = camp['axes'].get('queer', {}).get('score', 0)
        family_score = camp['axes'].get('family', {}).get('score', 0)
        print(f"{camp['rank']}. {camp['name']} (sober: {sober_score:.0f}, queer: {queer_score:.0f}, family: {family_score:.0f})")
else:
    print("✓ Correctly returned no results - this combination is too restrictive!")

print("\n" + "="*80)
print("TEST 5: Sober + LGBTQ+ (more realistic combination)")
print("="*80)

profile5 = UserProfile(sober=90, queer=90)
results5 = ranker.rank(profile5, top_k=10)

print(f"\nFound {len(results5)} camps\n")
if results5:
    for camp in results5[:5]:
        sober_score = camp['axes'].get('sober', {}).get('score', 0)
        queer_score = camp['axes'].get('queer', {}).get('score', 0)
        print(f"{camp['rank']}. {camp['name']} (sober: {sober_score:.0f}, queer: {queer_score:.0f})")
