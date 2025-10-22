#!/usr/bin/env python3
"""
Discover latent personality dimensions in camp data using statistical techniques.

Instead of guessing what personality axes exist, let's see what the data tells us!
"""

import json
import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from collections import Counter
import re

# Load camp personality features
features_path = Path(__file__).parent / 'camp_personality_features.json'
print(f"Loading camp features from {features_path}...")

with open(features_path) as f:
    camps = json.load(f)

print(f"Loaded {len(camps)} camps\n")

# Extract embeddings
embeddings = np.array([camp['embedding'] for camp in camps])
print(f"Embeddings shape: {embeddings.shape}\n")

# Load shaped camps for text analysis
shaped_path = Path(__file__).parent / 'shaped_camps.json'
with open(shaped_path) as f:
    shaped_camps = json.load(f)

# Create lookup by name
shaped_by_name = {camp['name']: camp for camp in shaped_camps}

print("="*80)
print("METHOD 1: PRINCIPAL COMPONENT ANALYSIS (PCA)")
print("="*80)
print("\nPCA finds the main axes of variation in the embedding space.")
print("Each component represents a latent dimension that differentiates camps.\n")

# Perform PCA
pca = PCA(n_components=10)
pca_components = pca.fit_transform(embeddings)

print(f"Explained variance by component:")
for i, var in enumerate(pca.explained_variance_ratio_):
    print(f"  Component {i+1}: {var*100:.2f}%")

print(f"\nCumulative variance explained by first 10 components: {sum(pca.explained_variance_ratio_)*100:.1f}%")

# Analyze each component by finding camps at extremes
print("\n" + "-"*80)
print("ANALYZING COMPONENTS BY EXTREMES")
print("-"*80)

for comp_idx in range(5):  # Analyze first 5 components
    print(f"\n{'='*80}")
    print(f"COMPONENT {comp_idx + 1} (explains {pca.explained_variance_ratio_[comp_idx]*100:.2f}% of variance)")
    print('='*80)

    # Get scores for this component
    scores = pca_components[:, comp_idx]

    # Find camps at high and low extremes
    high_indices = np.argsort(scores)[-10:][::-1]
    low_indices = np.argsort(scores)[:10]

    print("\nHIGH END (positive):")
    for idx in high_indices:
        camp = camps[idx]
        print(f"  {scores[idx]:7.2f}  {camp['name']}")

    print("\nLOW END (negative):")
    for idx in low_indices:
        camp = camps[idx]
        print(f"  {scores[idx]:7.2f}  {camp['name']}")

    # Analyze common words at each extreme
    print("\n--- Text Analysis ---")

    # Get text for high camps
    high_texts = []
    for idx in high_indices:
        name = camps[idx]['name']
        if name in shaped_by_name:
            high_texts.append(shaped_by_name[name]['text_corpus'].lower())

    # Get text for low camps
    low_texts = []
    for idx in low_indices:
        name = camps[idx]['name']
        if name in shaped_by_name:
            low_texts.append(shaped_by_name[name]['text_corpus'].lower())

    # Find distinctive words for high end
    high_words = Counter()
    for text in high_texts:
        words = re.findall(r'\b[a-z]{4,}\b', text)
        high_words.update(words)

    # Find distinctive words for low end
    low_words = Counter()
    for text in low_texts:
        words = re.findall(r'\b[a-z]{4,}\b', text)
        low_words.update(words)

    # Common words to filter out
    common_stopwords = {'camp', 'burning', 'black', 'rock', 'city', 'playa', 'year',
                       'event', 'people', 'time', 'will', 'come', 'join', 'bring',
                       'with', 'from', 'that', 'this', 'have', 'more', 'about',
                       'make', 'provide', 'offer', 'space', 'activities', 'welcome'}

    # Remove common words
    for word in common_stopwords:
        high_words.pop(word, None)
        low_words.pop(word, None)

    # Find words that are much more common in high vs low
    high_distinctive = []
    for word, count in high_words.most_common(30):
        low_count = low_words.get(word, 0)
        if count > low_count * 2:  # At least 2x more common
            high_distinctive.append((word, count, count / (low_count + 1)))

    # Find words that are much more common in low vs high
    low_distinctive = []
    for word, count in low_words.most_common(30):
        high_count = high_words.get(word, 0)
        if count > high_count * 2:  # At least 2x more common
            low_distinctive.append((word, count, count / (high_count + 1)))

    print("\nDistinctive words for HIGH end:")
    for word, count, ratio in sorted(high_distinctive, key=lambda x: x[2], reverse=True)[:15]:
        print(f"  {word:20s} (appears {count:3d}x, {ratio:.1f}x more than low)")

    print("\nDistinctive words for LOW end:")
    for word, count, ratio in sorted(low_distinctive, key=lambda x: x[2], reverse=True)[:15]:
        print(f"  {word:20s} (appears {count:3d}x, {ratio:.1f}x more than high)")

print("\n" + "="*80)
print("METHOD 2: CLUSTERING")
print("="*80)
print("\nK-Means clustering to find natural groups of similar camps.\n")

# Perform clustering
n_clusters = 8
kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
cluster_labels = kmeans.fit_predict(embeddings)

print(f"Created {n_clusters} clusters:\n")

for cluster_id in range(n_clusters):
    # Get camps in this cluster
    cluster_camps = [camps[i] for i, label in enumerate(cluster_labels) if label == cluster_id]

    print(f"\nCLUSTER {cluster_id + 1} ({len(cluster_camps)} camps)")
    print("-" * 40)

    # Sample camps
    print("Sample camps:")
    for camp in cluster_camps[:5]:
        print(f"  • {camp['name']}")

    # Analyze common words in this cluster
    cluster_texts = []
    for camp in cluster_camps[:20]:  # Sample first 20
        if camp['name'] in shaped_by_name:
            cluster_texts.append(shaped_by_name[camp['name']]['text_corpus'].lower())

    if cluster_texts:
        # Count words
        words = Counter()
        for text in cluster_texts:
            text_words = re.findall(r'\b[a-z]{4,}\b', text)
            words.update(text_words)

        # Remove stopwords
        for word in common_stopwords:
            words.pop(word, None)

        print("  Common themes:")
        for word, count in words.most_common(10):
            print(f"    {word} ({count})")

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

print("""
Based on this analysis:

1. Review the PCA components to see what themes emerge at the extremes
2. The distinctive words reveal what differentiates camps along each dimension
3. Clusters show natural groupings - what makes each cluster unique?

Next steps:
- Interpret what each PCA component represents (e.g., party vs quiet)
- Create more targeted personality axes based on what we discover
- Possibly use PCA scores directly as personality dimensions!
""")
