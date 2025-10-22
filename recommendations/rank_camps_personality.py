#!/usr/bin/env python3
"""
Personality-Based Camp Ranking Algorithm

Matches users to camps based on personality traits rather than explicit preferences.
This is more of a "personality quiz" feel than a search engine.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


class PersonalityProfile:
    """
    User's personality profile.

    Each axis is a spectrum from 0-100:
    - 0-25: Strong preference for left side of spectrum
    - 25-40: Moderate preference for left side
    - 40-60: Neutral / balanced
    - 60-75: Moderate preference for right side
    - 75-100: Strong preference for right side
    """

    def __init__(self, **traits):
        """
        Initialize personality profile.

        Args:
            **traits: Personality trait scores (0-100), e.g.:
                high_energy_social=80 (loves parties)
                early_bird=30 (night owl)
                hands_on_maker=90 (loves building)
        """
        self.traits = traits

    def __getattr__(self, name):
        if name == 'traits':
            return object.__getattribute__(self, name)
        return self.traits.get(name)


class PersonalityCampRanker:
    """Ranks camps based on personality matching"""

    def __init__(self, features_path: Optional[Path] = None):
        """
        Initialize ranker with camp personality features.

        Args:
            features_path: Path to camp_personality_features.json
        """
        if features_path is None:
            features_path = Path(__file__).parent / 'camp_personality_features.json'

        print(f"Loading camp personality features from {features_path}...")
        with open(features_path) as f:
            self.camps = json.load(f)

        print(f"Loaded {len(self.camps)} camps with personality profiles")

        # Pre-compute embedding matrix
        self.embeddings = np.array([camp['embedding'] for camp in self.camps])
        print(f"Embeddings shape: {self.embeddings.shape}")

    def rank(
        self,
        user_profile: PersonalityProfile,
        top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Rank camps for a user's personality profile.

        Args:
            user_profile: User's personality traits
            top_k: Number of top results to return

        Returns:
            List of ranked camps with scores and explanations
        """
        print(f"\nRanking camps for personality profile...")

        # Compute personality match scores
        personality_scores = self._compute_personality_match(user_profile)

        # Rank camps by personality match
        ranked_indices = np.argsort(personality_scores)[::-1]  # Descending

        # Build results
        results = []
        for idx in ranked_indices[:top_k]:
            camp = self.camps[idx]

            result = {
                'rank': len(results) + 1,
                'name': camp['name'],
                'uid': camp['uid'],
                'hometown': camp['hometown'],
                'score': float(personality_scores[idx]),

                # Personality match details
                'personality_match': float(personality_scores[idx]),

                # Axis scores
                'axes': camp['axes'],

                # Metadata
                'event_count': camp['event_count'],
                'years_active': camp['years_active']
            }

            # Generate explanation
            result['explanation'] = self._generate_explanation(
                result, user_profile
            )

            results.append(result)

        print(f"Ranked {len(results)} camps")
        return results

    def _compute_personality_match(self, user_profile: PersonalityProfile) -> np.ndarray:
        """
        Compute personality match scores for all camps.

        Uses a softer matching algorithm than before - we're looking for
        personality *similarity*, not perfect matches.

        Returns array of match scores (0-100) for all camps.
        """
        user_traits = {k: v for k, v in user_profile.traits.items() if v is not None}

        if not user_traits:
            # No personality info - return neutral scores
            return np.ones(len(self.camps)) * 50.0

        # Compute match score for each camp
        camp_match_scores = []

        for camp in self.camps:
            # For each trait, compute how well the camp matches
            trait_matches = []

            for trait_key, user_score in user_traits.items():
                # Skip if this trait doesn't exist in camp data
                if trait_key not in camp['axes']:
                    continue

                camp_score = camp['axes'][trait_key]['score']

                # Compute similarity using inverse distance
                # Distance of 0 = 100 match, distance of 100 = 0 match
                distance = abs(user_score - camp_score)
                match = 100 - distance

                trait_matches.append(match)

            # Average match across all traits
            if trait_matches:
                avg_match = np.mean(trait_matches)
            else:
                avg_match = 50.0  # Neutral

            camp_match_scores.append(avg_match)

        return np.array(camp_match_scores)

    def _generate_explanation(
        self,
        result: Dict[str, Any],
        user_profile: PersonalityProfile
    ) -> str:
        """Generate human-readable explanation for why this camp matches"""

        explanations = []

        # Find the top 3 matching personality traits
        user_traits = {k: v for k, v in user_profile.traits.items() if v is not None}
        trait_matches = []

        for trait_key, user_score in user_traits.items():
            if trait_key not in result['axes']:
                continue

            camp_score = result['axes'][trait_key]['score']
            distance = abs(user_score - camp_score)

            # Good match if within 30 points
            if distance <= 30:
                trait_matches.append({
                    'trait': trait_key,
                    'name': result['axes'][trait_key]['name'],
                    'distance': distance,
                    'user_score': user_score,
                    'camp_score': camp_score
                })

        # Sort by best match
        trait_matches.sort(key=lambda x: x['distance'])

        # Add top matching traits to explanation
        for match in trait_matches[:3]:
            trait_name = match['name'].replace(' ', ' ').lower()
            if match['camp_score'] >= 60:
                explanations.append(f"High {trait_name}")
            elif match['camp_score'] >= 40:
                explanations.append(f"Balanced {trait_name}")
            else:
                explanations.append(f"Low {trait_name}")

        # Active camp
        if result['years_active'] >= 5:
            explanations.append(f"{result['years_active']} years on playa")

        # Event-rich
        if result['event_count'] >= 50:
            explanations.append(f"{result['event_count']} events")

        if not explanations:
            explanations.append("Interesting vibe match")

        return ", ".join(explanations[:4])  # Limit to top 4 reasons


def demo():
    """Demonstration with example personality profiles"""

    print("\n" + "="*80)
    print("PERSONALITY-BASED CAMP MATCHING DEMO")
    print("="*80)

    ranker = PersonalityCampRanker()

    # Example 1: High-energy social party animal
    print("\n" + "-"*80)
    print("EXAMPLE 1: High-Energy Social Butterfly")
    print("-"*80)
    print("Personality: Loves parties, night owl, playful, large crowds")

    profile1 = PersonalityProfile(
        high_energy_social=90,
        night_owl=80,
        playful_prankster=85,
        large_scale_spectacle=75
    )

    results1 = ranker.rank(profile1, top_k=10)

    print("\nTop 10 matches:\n")
    for camp in results1:
        print(f"{camp['rank']}. {camp['name']} (match: {camp['score']:.1f}%)")
        print(f"   {camp['explanation']}")
        print()

    # Example 2: Quiet contemplative maker
    print("\n" + "-"*80)
    print("EXAMPLE 2: Quiet Contemplative Maker")
    print("-"*80)
    print("Personality: Introverted, morning person, hands-on, small groups")

    profile2 = PersonalityProfile(
        quiet_contemplative=85,
        early_bird=80,
        hands_on_maker=90,
        intimate_small_scale=75
    )

    results2 = ranker.rank(profile2, top_k=10)

    print("\nTop 10 matches:\n")
    for camp in results2:
        print(f"{camp['rank']}. {camp['name']} (match: {camp['score']:.1f}%)")
        print(f"   {camp['explanation']}")
        print()

    print("\n" + "="*80)
    print("✓ DEMO COMPLETE")
    print("="*80)


if __name__ == '__main__':
    demo()
