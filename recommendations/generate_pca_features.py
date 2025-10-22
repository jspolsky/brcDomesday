#!/usr/bin/env python3
"""
Generate camp features using PCA-discovered personality dimensions.

Instead of guessing personality axes with keywords, we use the actual
latent dimensions discovered by PCA on the embedding space.
"""

import json
import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA

print("="*80)
print("GENERATING PCA-BASED PERSONALITY FEATURES")
print("="*80)

# Load existing personality features (for embeddings)
features_path = Path(__file__).parent / 'camp_personality_features.json'
print(f"\nLoading camp features from {features_path}...")

with open(features_path) as f:
    camps = json.load(f)

print(f"Loaded {len(camps)} camps")

# Extract embeddings
embeddings = np.array([camp['embedding'] for camp in camps])
print(f"Embeddings shape: {embeddings.shape}")

# Perform PCA with 8 components (for 8 personality questions)
print("\nPerforming PCA with 8 components...")
pca = PCA(n_components=8)
pca_scores = pca.fit_transform(embeddings)

print(f"PCA scores shape: {pca_scores.shape}")
print(f"\nExplained variance by component:")
for i, var in enumerate(pca.explained_variance_ratio_):
    print(f"  Component {i+1}: {var*100:.2f}%")

cumulative_var = sum(pca.explained_variance_ratio_)
print(f"\nCumulative variance explained: {cumulative_var*100:.1f}%")

# Define interpretations for each PCA component
# Based on our analysis of the extremes
COMPONENT_INTERPRETATIONS = {
    0: {
        'positive_name': 'Hospitality Provider',
        'negative_name': 'Art Creator',
        'positive_desc': 'Loves providing service - coffee, drinks, food, comfort',
        'negative_desc': 'Focused on creating art, building projects, collaboration'
    },
    1: {
        'positive_name': 'Wellness Seeker',
        'negative_name': 'Simple & Direct',
        'positive_desc': 'Seeks wellness, sanctuary, self-care, deep connection',
        'negative_desc': 'Straightforward, uncomplicated, direct experiences'
    },
    2: {
        'positive_name': 'Entertainment Lover',
        'negative_name': 'Sacred Practitioner',
        'positive_desc': 'Loves shows, performances, films, entertainment spectacles',
        'negative_desc': 'Drawn to sacred practices, workshops, feminine energy, healing'
    },
    3: {
        'positive_name': 'Dance & Movement',
        'negative_name': 'Rest & Relaxation',
        'positive_desc': 'High energy, dance, movement, active participation',
        'negative_desc': 'Prefers massage, rest, chill spaces, rejuvenation'
    },
    4: {
        'positive_name': 'Community Gatherer',
        'negative_name': 'Practical Support',
        'positive_desc': 'Loves group activities, community, togetherness',
        'negative_desc': 'Values practical infrastructure and support systems'
    },
    5: {
        'positive_name': 'Dimension 6',
        'negative_name': 'Dimension 6 (opposite)',
        'positive_desc': 'High on 6th latent dimension',
        'negative_desc': 'Low on 6th latent dimension'
    },
    6: {
        'positive_name': 'Dimension 7',
        'negative_name': 'Dimension 7 (opposite)',
        'positive_desc': 'High on 7th latent dimension',
        'negative_desc': 'Low on 7th latent dimension'
    },
    7: {
        'positive_name': 'Dimension 8',
        'negative_name': 'Dimension 8 (opposite)',
        'positive_desc': 'High on 8th latent dimension',
        'negative_desc': 'Low on 8th latent dimension'
    }
}

# Normalize PCA scores to 0-100 scale for each component
# 0 = negative extreme, 50 = neutral, 100 = positive extreme
print("\nNormalizing PCA scores to 0-100 scale...")

normalized_scores = np.zeros_like(pca_scores)

for i in range(pca_scores.shape[1]):
    scores = pca_scores[:, i]

    # Get min and max for this component
    min_score = np.min(scores)
    max_score = np.max(scores)

    # Normalize to 0-100
    # min -> 0, 0 -> 50, max -> 100
    normalized = 50 + (scores / max(abs(min_score), abs(max_score))) * 50
    normalized_scores[:, i] = normalized

    print(f"  Component {i+1}: [{min_score:.2f}, {max_score:.2f}] -> [0, 100]")

# Build new feature records with PCA-based personality dimensions
print("\nBuilding PCA-based feature records...")

pca_features = []

for i, camp in enumerate(camps):
    feature = {
        'name': camp['name'],
        'uid': camp['uid'],
        'hometown': camp['hometown'],
        'years_active': camp['years_active'],
        'event_count': camp['event_count'],
        'embedding': camp['embedding'],
        'pca_personality': {}
    }

    # Add PCA component scores as personality dimensions
    for comp_idx in range(8):
        interp = COMPONENT_INTERPRETATIONS[comp_idx]

        # The score represents position on the spectrum
        # 0-50: more like negative_name
        # 50-100: more like positive_name
        score = float(normalized_scores[i, comp_idx])

        feature['pca_personality'][f'component_{comp_idx+1}'] = {
            'score': score,
            'positive_trait': interp['positive_name'],
            'negative_trait': interp['negative_name']
        }

    pca_features.append(feature)

# Save to file
output_path = Path(__file__).parent / 'camp_pca_features.json'
print(f"\nSaving to {output_path}...")

with open(output_path, 'w') as f:
    json.dump(pca_features, f, indent=2)

file_size = output_path.stat().st_size / (1024 * 1024)
print(f"✓ Saved {len(pca_features)} camp features ({file_size:.1f} MB)")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

print(f"\nGenerated PCA-based features for {len(pca_features)} camps")
print(f"Using {pca_scores.shape[1]} PCA components as personality dimensions")
print(f"Total variance captured: {cumulative_var*100:.1f}%")

print("\n8 Personality Spectrums (from PCA):")
for i in range(8):
    interp = COMPONENT_INTERPRETATIONS[i]
    print(f"  {i+1}. {interp['negative_name']} ↔️ {interp['positive_name']}")

print("\n" + "="*80)
print("✓ PCA-BASED FEATURES GENERATED!")
print("="*80)
print("\nNext: Update ranking algorithm to use PCA scores")
print("Next: Update quiz to ask questions about these dimensions")
