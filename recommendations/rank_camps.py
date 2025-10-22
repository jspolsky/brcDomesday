#!/usr/bin/env python3
"""
Camp Ranking Algorithm for BRC Camp Recommendation Engine

Takes a user profile (axis preferences + optional text) and ranks camps
by combining:
1. Embedding similarity (semantic match)
2. Axis score matching (preference alignment)

Usage:
    from rank_camps import CampRanker
    ranker = CampRanker()
    results = ranker.rank(user_profile)
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


class UserProfile:
    """
    User preferences for camp matching.

    Can accept any axis name as a keyword argument.
    Axis preferences are 0-100 scale, None means "don't care about this axis"
    """

    def __init__(self, description: Optional[str] = None, hometown: Optional[str] = None, **axes):
        """
        Initialize user profile.

        Args:
            description: Optional text description of ideal camp
            hometown: Optional hometown for geographic bonus
            **axes: Axis preferences (0-100 scale), e.g. music_jazz_blues=90, woo_woo=20
        """
        self.description = description
        self.hometown = hometown
        self.axes = axes

    def __getattr__(self, name):
        """Allow accessing axes as attributes"""
        if name in ['description', 'hometown', 'axes']:
            return object.__getattribute__(self, name)
        return self.axes.get(name)


class CampRanker:
    """Ranks camps based on user preferences"""

    def __init__(self, features_path: Optional[Path] = None):
        """
        Initialize ranker with camp features.

        Args:
            features_path: Path to camp_features.json (defaults to same directory)
        """
        if features_path is None:
            features_path = Path(__file__).parent / 'camp_features.json'

        print(f"Loading camp features from {features_path}...")
        with open(features_path) as f:
            self.camps = json.load(f)

        print(f"Loaded {len(self.camps)} camps")

        # Pre-compute embedding matrix for efficient similarity search
        self.embeddings = np.array([camp['embedding'] for camp in self.camps])
        print(f"Embeddings shape: {self.embeddings.shape}")

        # Load sentence transformer for text-based queries
        self.model = None  # Lazy load

    def _load_model(self):
        """Lazy load sentence transformer model"""
        if self.model is None:
            print("Loading sentence transformer model...")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def _compute_embedding_similarity(self, user_profile: UserProfile) -> np.ndarray:
        """
        Compute embedding similarity scores.

        Returns array of similarity scores (0-1) for all camps.
        """
        if user_profile.description is None:
            # No text description - return neutral scores
            return np.ones(len(self.camps)) * 0.5

        # Generate embedding for user's description
        self._load_model()
        user_embedding = self.model.encode(
            [user_profile.description],
            normalize_embeddings=True
        )[0]

        # Compute cosine similarity with all camps
        # (embeddings are already normalized, so dot product = cosine similarity)
        similarities = np.dot(self.embeddings, user_embedding)

        return similarities

    def _compute_axis_match_score(self, user_profile: UserProfile) -> np.ndarray:
        """
        Compute axis matching scores.

        For each axis where user has a preference, compute how well each camp matches.
        Returns array of match scores (0-100) for all camps.
        """
        # Collect preferences that are set (from user_profile.axes dict)
        user_preferences = {k: v for k, v in user_profile.axes.items() if v is not None}

        if not user_preferences:
            # No axis preferences - return neutral scores
            return np.ones(len(self.camps)) * 50.0

        # Compute match score for each camp
        camp_match_scores = []

        for camp in self.camps:
            # For each axis, compute distance from user preference
            axis_distances = []

            for axis_key, user_pref in user_preferences.items():
                # Skip if this axis doesn't exist in camp data
                if axis_key not in camp['axes']:
                    continue

                camp_score = camp['axes'][axis_key]['score']

                # Compute match score
                # If camp score >= user preference, give 100 + small bonus for excess
                # If camp score < user preference, penalize by the distance
                if camp_score >= user_pref:
                    # Camp meets or exceeds user preference - excellent!
                    # Give 100 base + small bonus for how much more (up to 10 points)
                    excess = min(camp_score - user_pref, 10)
                    match = 100 + excess
                else:
                    # Camp has less than user wants - penalize by distance
                    distance = user_pref - camp_score
                    match = 100 - distance

                axis_distances.append(match)

            # Average match across all axes user cares about
            avg_match = np.mean(axis_distances)
            camp_match_scores.append(avg_match)

        return np.array(camp_match_scores)

    def _compute_geographic_bonus(self, user_profile: UserProfile) -> np.ndarray:
        """
        Compute geographic bonus for camps from same area.

        Returns array of bonus scores (0-10) for all camps.
        """
        if user_profile.hometown is None:
            return np.zeros(len(self.camps))

        user_hometown = user_profile.hometown.lower().strip()
        bonuses = []

        for camp in self.camps:
            camp_hometown = camp.get('hometown', '').lower().strip()

            # Exact match
            if camp_hometown == user_hometown:
                bonuses.append(10.0)
            # Partial match (one contains the other)
            elif user_hometown in camp_hometown or camp_hometown in user_hometown:
                bonuses.append(5.0)
            else:
                bonuses.append(0.0)

        return np.array(bonuses)

    def rank(
        self,
        user_profile: UserProfile,
        top_k: int = 50,
        embedding_weight: float = 0.3,
        axis_weight: float = 0.7,
        geographic_weight: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Rank camps for a user profile.

        Args:
            user_profile: User's preferences
            top_k: Number of top results to return
            embedding_weight: Weight for embedding similarity (default 0.3)
            axis_weight: Weight for axis matching (default 0.7)
            geographic_weight: Weight for geographic bonus (default 0.1)

        Returns:
            List of ranked camps with scores and explanations
        """
        print(f"\nRanking camps for user profile...")

        # Compute component scores
        embedding_scores = self._compute_embedding_similarity(user_profile)
        axis_scores = self._compute_axis_match_score(user_profile)
        geo_bonuses = self._compute_geographic_bonus(user_profile)

        # Normalize embedding scores to 0-100 scale
        embedding_scores_normalized = embedding_scores * 100

        # Compute final scores
        # Note: geographic bonus is additive, not weighted
        final_scores = (
            embedding_weight * embedding_scores_normalized +
            axis_weight * axis_scores +
            geographic_weight * geo_bonuses
        )

        # Rank camps
        ranked_indices = np.argsort(final_scores)[::-1]  # Descending order

        # Build results
        results = []
        for idx in ranked_indices[:top_k]:
            camp = self.camps[idx]

            result = {
                'rank': len(results) + 1,
                'name': camp['name'],
                'uid': camp['uid'],
                'hometown': camp['hometown'],
                'score': float(final_scores[idx]),

                # Component scores for explanation
                'component_scores': {
                    'embedding_similarity': float(embedding_scores[idx] * 100),
                    'axis_match': float(axis_scores[idx]),
                    'geographic_bonus': float(geo_bonuses[idx])
                },

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

    def _generate_explanation(
        self,
        result: Dict[str, Any],
        user_profile: UserProfile
    ) -> str:
        """Generate human-readable explanation for why this camp was recommended"""

        explanations = []

        # Check which axes match well (use user preferences)
        # Create readable names from axis keys
        def readable_name(axis_key):
            # music_jazz_blues -> Jazz/Blues, woo_woo -> Spirituality, etc.
            if axis_key.startswith('music_'):
                name = axis_key.replace('music_', '').replace('_', '/').title()
                return name.replace('Hiphop', 'Hip Hop')
            return axis_key.replace('_', ' ').title()

        for axis_key, user_pref in user_profile.axes.items():
            if user_pref is None or axis_key not in result['axes']:
                continue

            camp_score = result['axes'][axis_key]['score']

            # Good match if within 20 points
            if abs(user_pref - camp_score) <= 20:
                axis_name = readable_name(axis_key)
                if camp_score >= 70:
                    explanations.append(f"High {axis_name.lower()}")
                elif camp_score >= 40:
                    explanations.append(f"Medium {axis_name.lower()}")
                elif camp_score <= 20:
                    explanations.append(f"Low {axis_name.lower()}")

        # Geographic match
        if result['component_scores']['geographic_bonus'] > 0:
            explanations.append(f"From {result['hometown']}")

        # Active camp
        if result['years_active'] >= 5:
            explanations.append(f"{result['years_active']} years on playa")

        # Event-rich
        if result['event_count'] >= 50:
            explanations.append(f"{result['event_count']} events")

        if not explanations:
            explanations.append("Good overall match")

        return ", ".join(explanations[:4])  # Limit to top 4 reasons


def print_results(results: List[Dict[str, Any]], top_n: int = 20):
    """Pretty print ranking results"""
    print("\n" + "=" * 80)
    print(f"TOP {top_n} RECOMMENDED CAMPS")
    print("=" * 80)

    for result in results[:top_n]:
        print(f"\n#{result['rank']}. {result['name']}")
        print(f"  Score: {result['score']:.1f}")
        print(f"  {result['explanation']}")
        print(f"  Hometown: {result['hometown']}")

        # Show axis scores
        print(f"  Axes: ", end="")
        axis_strs = []
        for axis_key, axis_data in result['axes'].items():
            if axis_data['score'] >= 40:  # Only show significant axes
                axis_strs.append(f"{axis_key}={axis_data['score']:.0f}")
        print(", ".join(axis_strs))


def demo():
    """Demonstration of ranking with example user profiles"""

    print("\n" + "=" * 80)
    print("CAMP RANKING DEMONSTRATION")
    print("=" * 80)

    ranker = CampRanker()

    # Example 1: Spiritual workshop seeker
    print("\n" + "-" * 80)
    print("EXAMPLE 1: Spiritual Workshop Seeker")
    print("-" * 80)
    print("Profile: High woo-woo, high workshops, low sound/party")

    profile1 = UserProfile(
        woo_woo=90,
        workshops=85,
        sound_party=20,
        description="I'm looking for a contemplative space with meditation, "
                   "healing workshops, and spiritual practices. I prefer quiet "
                   "environments over loud parties."
    )

    results1 = ranker.rank(profile1, top_k=20)
    print_results(results1, top_n=10)

    # Example 2: Party animal
    print("\n" + "-" * 80)
    print("EXAMPLE 2: Party Animal")
    print("-" * 80)
    print("Profile: High sound/party, high hospitality, low woo-woo")

    profile2 = UserProfile(
        sound_party=95,
        hospitality=80,
        woo_woo=10,
        description="I want to dance all night at camps with amazing sound systems, "
                   "DJs, and bars. Give me music, beats, and high energy!"
    )

    results2 = ranker.rank(profile2, top_k=20)
    print_results(results2, top_n=10)

    # Example 3: Sober queer person seeking community
    print("\n" + "-" * 80)
    print("EXAMPLE 3: Sober LGBTQ+ Community Seeker")
    print("-" * 80)
    print("Profile: High sober, high queer, medium workshops")

    profile3 = UserProfile(
        sober=90,
        queer=90,
        workshops=60,
        description="I'm a sober queer person looking for affirming spaces "
                   "with recovery support and LGBTQ+ community."
    )

    results3 = ranker.rank(profile3, top_k=20)
    print_results(results3, top_n=10)

    # Example 4: Family with kids
    print("\n" + "-" * 80)
    print("EXAMPLE 4: Family with Kids")
    print("-" * 80)
    print("Profile: High family, high art, medium workshops, low sound/party")

    profile4 = UserProfile(
        family=95,
        art=75,
        workshops=60,
        sound_party=25,
        description="Looking for family-friendly camps with activities for kids, "
                   "art projects, and a welcoming daytime vibe."
    )

    results4 = ranker.rank(profile4, top_k=20)
    print_results(results4, top_n=10)

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    demo()
