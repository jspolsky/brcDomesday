#!/usr/bin/env python3
"""
PCA-Based Camp Ranking Algorithm

Matches users to camps using PCA-discovered latent personality dimensions.
These are dimensions that ACTUALLY exist in the data, not our guesses!
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any


class PCAPersonalityProfile:
    """
    User's personality profile based on PCA components.

    Each component is a score from 0-100 representing position on a spectrum:
    - 0-50: More aligned with negative trait
    - 50-100: More aligned with positive trait
    """

    def __init__(self, **components):
        """
        Initialize PCA personality profile.

        Args:
            **components: PCA component scores (0-100), e.g.:
                component_1=80 (more hospitality provider)
                component_3=30 (more sacred practitioner)
        """
        self.components = components

    def __getattr__(self, name):
        if name == 'components':
            return object.__getattribute__(self, name)
        return self.components.get(name)


class PCACampRanker:
    """Ranks camps based on PCA personality matching"""

    def __init__(self, features_path: Path = None):
        """
        Initialize ranker with PCA-based camp features.

        Args:
            features_path: Path to camp_pca_features.json
        """
        if features_path is None:
            features_path = Path(__file__).parent / 'camp_pca_features.json'

        print(f"Loading PCA-based camp features from {features_path}...")
        with open(features_path) as f:
            self.camps = json.load(f)

        print(f"Loaded {len(self.camps)} camps with PCA personality profiles")

    def rank(
        self,
        user_profile: PCAPersonalityProfile,
        top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Rank camps for a user's PCA personality profile.

        Args:
            user_profile: User's PCA component scores
            top_k: Number of top results to return

        Returns:
            List of ranked camps with scores and explanations
        """
        print(f"\nRanking camps using PCA personality matching...")

        # Compute PCA personality match scores
        personality_scores = self._compute_pca_match(user_profile)

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

                # PCA personality details
                'pca_match': float(personality_scores[idx]),
                'pca_personality': camp['pca_personality'],

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

    def _compute_pca_match(self, user_profile: PCAPersonalityProfile) -> np.ndarray:
        """
        Compute PCA personality match scores for all camps.

        Uses inverse distance on PCA component space.

        Returns array of match scores (0-100) for all camps.
        """
        user_components = {k: v for k, v in user_profile.components.items() if v is not None}

        if not user_components:
            # No personality info - return neutral scores
            return np.ones(len(self.camps)) * 50.0

        # Compute match score for each camp
        camp_match_scores = []

        for camp in self.camps:
            # For each PCA component, compute similarity
            component_matches = []

            for comp_key, user_score in user_components.items():
                # Get camp's score on this component
                if comp_key not in camp['pca_personality']:
                    continue

                camp_score = camp['pca_personality'][comp_key]['score']

                # Compute similarity using inverse distance
                distance = abs(user_score - camp_score)
                match = 100 - distance

                component_matches.append(match)

            # Average match across all components
            if component_matches:
                avg_match = np.mean(component_matches)
            else:
                avg_match = 50.0  # Neutral

            camp_match_scores.append(avg_match)

        return np.array(camp_match_scores)

    def _generate_explanation(
        self,
        result: Dict[str, Any],
        user_profile: PCAPersonalityProfile
    ) -> str:
        """Generate human-readable explanation for why this camp matches"""

        explanations = []

        # Find the top 3 matching PCA components
        user_components = {k: v for k, v in user_profile.components.items() if v is not None}
        component_matches = []

        for comp_key, user_score in user_components.items():
            if comp_key not in result['pca_personality']:
                continue

            camp_data = result['pca_personality'][comp_key]
            camp_score = camp_data['score']
            distance = abs(user_score - camp_score)

            # Good match if within 30 points
            if distance <= 30:
                component_matches.append({
                    'component': comp_key,
                    'distance': distance,
                    'user_score': user_score,
                    'camp_score': camp_score,
                    'positive_trait': camp_data['positive_trait'],
                    'negative_trait': camp_data['negative_trait']
                })

        # Sort by best match
        component_matches.sort(key=lambda x: x['distance'])

        # Add top matching traits to explanation
        for match in component_matches[:3]:
            # Determine which trait to mention based on camp's score
            if match['camp_score'] >= 60:
                trait = match['positive_trait'].lower()
            elif match['camp_score'] <= 40:
                trait = match['negative_trait'].lower()
            else:
                trait = f"balanced {match['positive_trait'].lower()}/{match['negative_trait'].lower()}"

            explanations.append(trait)

        # Active camp
        if result['years_active'] >= 5:
            explanations.append(f"{result['years_active']} years on playa")

        # Event-rich
        if result['event_count'] >= 50:
            explanations.append(f"{result['event_count']} events")

        if not explanations:
            explanations.append("Interesting personality match")

        # Capitalize first letter
        explanation = ", ".join(explanations[:4])
        return explanation[0].upper() + explanation[1:] if explanation else "Good match"


def demo():
    """Demonstration with example PCA personalities"""

    print("\n" + "="*80)
    print("PCA-BASED PERSONALITY MATCHING DEMO")
    print("="*80)

    ranker = PCACampRanker()

    # Example 1: Hospitality provider who loves wellness
    print("\n" + "-"*80)
    print("EXAMPLE 1: Hospitality Provider + Wellness Seeker")
    print("-"*80)
    print("Personality: Loves providing service and wellness experiences")

    profile1 = PCAPersonalityProfile(
        component_1=80,  # Hospitality provider
        component_2=80   # Wellness seeker
    )

    results1 = ranker.rank(profile1, top_k=10)

    print("\nTop 10 matches:\n")
    for camp in results1:
        print(f"{camp['rank']}. {camp['name']} (match: {camp['score']:.1f}%)")
        print(f"   {camp['explanation']}")
        print()

    # Example 2: Art creator who loves sacred practices
    print("\n" + "-"*80)
    print("EXAMPLE 2: Art Creator + Sacred Practitioner")
    print("-"*80)
    print("Personality: Creates art and drawn to sacred, workshop-based spaces")

    profile2 = PCAPersonalityProfile(
        component_1=20,  # Art creator (low on component 1)
        component_3=20   # Sacred practitioner (low on component 3)
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
