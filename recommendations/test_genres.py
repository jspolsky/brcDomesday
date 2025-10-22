#!/usr/bin/env python3
"""
Test the updated ranking algorithm with music genre preferences
"""

from rank_camps import CampRanker, UserProfile

def test_jazz_lover():
    """Test Jazz lover finding Playa Jazz Cafe"""
    print("\n" + "=" * 80)
    print("TEST: JAZZ LOVER")
    print("=" * 80)

    ranker = CampRanker()

    profile = UserProfile(
        music_jazz_blues=95,
        music_classical=70,
        music_electronic=10,
        description="I love jazz, blues, and live improvisation. Looking for sophisticated music camps."
    )

    results = ranker.rank(profile, top_k=10)

    print("\nTop 10 results:\n")
    for camp in results:
        print(f"{camp['rank']}. {camp['name']} (score: {camp['score']:.1f})")
        print(f"   {camp['explanation']}")

        # Show jazz/blues score
        if 'music_jazz_blues' in camp['axes']:
            jazz_score = camp['axes']['music_jazz_blues']['score']
            print(f"   Jazz/Blues score: {jazz_score:.0f}")
        print()


def test_latin_dancer():
    """Test Latin music lover"""
    print("\n" + "=" * 80)
    print("TEST: LATIN MUSIC DANCER")
    print("=" * 80)

    ranker = CampRanker()

    profile = UserProfile(
        music_latin=95,
        music_disco_funk=70,
        hospitality=60,
        description="I love salsa, cumbia, and Latin rhythms. Want to dance!"
    )

    results = ranker.rank(profile, top_k=10)

    print("\nTop 10 results:\n")
    for camp in results:
        print(f"{camp['rank']}. {camp['name']} (score: {camp['score']:.1f})")
        print(f"   {camp['explanation']}")

        # Show Latin score
        if 'music_latin' in camp['axes']:
            latin_score = camp['axes']['music_latin']['score']
            print(f"   Latin Music score: {latin_score:.0f}")
        print()


def test_classical_fan():
    """Test Classical music fan finding Playa Choir"""
    print("\n" + "=" * 80)
    print("TEST: CLASSICAL MUSIC FAN")
    print("=" * 80)

    ranker = CampRanker()

    profile = UserProfile(
        music_classical=90,
        music_ambient_chill=60,
        music_electronic=15,
        description="I love orchestras, choirs, and classical chamber music."
    )

    results = ranker.rank(profile, top_k=10)

    print("\nTop 10 results:\n")
    for camp in results:
        print(f"{camp['rank']}. {camp['name']} (score: {camp['score']:.1f})")
        print(f"   {camp['explanation']}")

        # Show classical score
        if 'music_classical' in camp['axes']:
            classical_score = camp['axes']['music_classical']['score']
            print(f"   Classical/Orchestra score: {classical_score:.0f}")
        print()


def test_eclectic_music_lover():
    """Test someone who likes multiple genres"""
    print("\n" + "=" * 80)
    print("TEST: ECLECTIC MUSIC LOVER")
    print("=" * 80)

    ranker = CampRanker()

    profile = UserProfile(
        music_electronic=80,
        music_disco_funk=75,
        music_world_tribal=70,
        music_live_bands=65,
        hospitality=80,
        description="I love all kinds of music - electronic, disco, world music, live bands. Variety is key!"
    )

    results = ranker.rank(profile, top_k=10)

    print("\nTop 10 results:\n")
    for camp in results:
        print(f"{camp['rank']}. {camp['name']} (score: {camp['score']:.1f})")
        print(f"   {camp['explanation']}")

        # Show top 3 music scores
        music_scores = {k: v['score'] for k, v in camp['axes'].items() if k.startswith('music_') and v['score'] > 30}
        if music_scores:
            top_3 = sorted(music_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"   Music genres: {', '.join(f'{k.replace('music_', '')}: {v:.0f}' for k, v in top_3)}")
        print()


if __name__ == '__main__':
    test_jazz_lover()
    test_latin_dancer()
    test_classical_fan()
    test_eclectic_music_lover()
