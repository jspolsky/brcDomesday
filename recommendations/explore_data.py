#!/usr/bin/env python3
"""
Exploratory Data Analysis for BRC Camp Recommendation Engine
Analyzes camps.json and campHistory.json to understand data characteristics
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import statistics

def load_data():
    """Load camps and history data"""
    data_dir = Path(__file__).parent.parent / 'data'

    with open(data_dir / 'camps.json') as f:
        camps = json.load(f)

    with open(data_dir / 'campHistory.json') as f:
        history = json.load(f)

    return camps, history


def analyze_basic_stats(camps, history):
    """Basic statistics about the datasets"""
    print("=" * 80)
    print("BASIC STATISTICS")
    print("=" * 80)
    print(f"Total camps in 2025: {len(camps)}")
    print(f"Total camps in history: {len(history)}")
    print()

    # Check which camps have history
    camps_with_history = sum(1 for c in camps if c['name'] in history)
    print(f"2025 camps with historical data: {camps_with_history} ({camps_with_history/len(camps)*100:.1f}%)")
    print()

    # Years of history
    years_count = []
    for camp_name, camp_data in history.items():
        years_count.append(len(camp_data['history']))

    print(f"Average years of history per camp: {statistics.mean(years_count):.1f}")
    print(f"Median years of history: {statistics.median(years_count)}")
    print(f"Max years of history: {max(years_count)}")
    print(f"Min years of history: {min(years_count)}")
    print()

    # Distribution of years
    year_dist = Counter(years_count)
    print("Distribution of historical years:")
    for years in sorted(year_dist.keys()):
        print(f"  {years} years: {year_dist[years]} camps")
    print()


def analyze_text_fields(camps, history):
    """Analyze text content availability and length"""
    print("=" * 80)
    print("TEXT CONTENT ANALYSIS")
    print("=" * 80)

    # Description lengths
    desc_lengths = [len(c.get('description', '')) for c in camps if c.get('description')]
    has_description = sum(1 for c in camps if c.get('description'))

    print(f"Camps with descriptions: {has_description}/{len(camps)} ({has_description/len(camps)*100:.1f}%)")
    if desc_lengths:
        print(f"Average description length: {statistics.mean(desc_lengths):.0f} chars")
        print(f"Median description length: {statistics.median(desc_lengths):.0f} chars")
        print(f"Max description length: {max(desc_lengths)} chars")
        print(f"Min description length: {min(desc_lengths)} chars")
    print()

    # Event data
    total_events = 0
    camps_with_events = 0
    event_text_lengths = []

    for camp_name, camp_data in history.items():
        camp_has_events = False
        for year_data in camp_data['history']:
            events = year_data.get('events', [])
            if events:
                camp_has_events = True
                total_events += len(events)
                for event in events:
                    title = event.get('title', '')
                    desc = event.get('description', '')
                    event_text_lengths.append(len(title) + len(desc))
        if camp_has_events:
            camps_with_events += 1

    print(f"Total events across all years: {total_events:,}")
    print(f"Camps with events (any year): {camps_with_events}/{len(history)} ({camps_with_events/len(history)*100:.1f}%)")
    if event_text_lengths:
        print(f"Average event text length: {statistics.mean(event_text_lengths):.0f} chars")
        print(f"Total event text corpus: {sum(event_text_lengths):,} chars")
    print()


def analyze_hometowns(camps):
    """Analyze geographic distribution"""
    print("=" * 80)
    print("GEOGRAPHIC DISTRIBUTION (Hometowns)")
    print("=" * 80)

    hometowns = [c.get('hometown', '').lower().strip() for c in camps if c.get('hometown')]
    hometown_counts = Counter(hometowns)

    print(f"Camps with hometown data: {len(hometowns)}/{len(camps)} ({len(hometowns)/len(camps)*100:.1f}%)")
    print(f"Unique hometowns: {len(hometown_counts)}")
    print()
    print("Top 20 hometowns:")
    for hometown, count in hometown_counts.most_common(20):
        print(f"  {hometown}: {count}")
    print()


def extract_keywords(text, keywords):
    """Count keyword occurrences in text (case-insensitive, word boundaries)"""
    text_lower = text.lower()
    counts = {}
    for keyword in keywords:
        # Use word boundaries for better matching
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        counts[keyword] = len(re.findall(pattern, text_lower))
    return counts


def analyze_potential_axes(camps, history):
    """Analyze potential feature axes based on keyword presence"""
    print("=" * 80)
    print("POTENTIAL FEATURE AXES ANALYSIS")
    print("=" * 80)

    # Define keyword sets for different axes
    axes = {
        'Woo-woo / Spirituality': [
            'chakra', 'chakras', 'energy healing', 'reiki', 'astrology', 'oracle',
            'breathwork', 'tantra', 'shamanic', 'sound bath', 'meditation',
            'spiritual', 'healing', 'crystal', 'tarot'
        ],
        'Science / Skeptical': [
            'science', 'skeptic', 'rational', 'evidence', 'research',
            'astronomy', 'physics', 'chemistry', 'biology', 'math', 'mathematics'
        ],
        'Sound / Party': [
            'dj', 'music', 'dance', 'party', 'beats', 'sound camp', 'stage',
            'techno', 'house music', 'bass', 'rave', 'nightclub', 'disco'
        ],
        'Workshops / Learning': [
            'workshop', 'class', 'learn', 'teach', 'lecture', 'seminar',
            'talk', 'panel', 'discussion', 'education', 'skill'
        ],
        'Maker / Engineering': [
            'maker', 'build', 'engineering', 'welding', 'electronics',
            'solder', 'arduino', '3d print', 'cnc', 'woodworking', 'metal'
        ],
        'Fitness / Body': [
            'yoga', 'fitness', 'workout', 'exercise', 'acro', 'acrobat',
            'run', 'running', 'dance', 'movement', 'stretching', 'pilates'
        ],
        'Food / Hospitality': [
            'bar', 'drinks', 'coffee', 'tea', 'food', 'kitchen', 'meal',
            'breakfast', 'brunch', 'dinner', 'feast', 'restaurant', 'cafe'
        ],
        'LGBTQ+ / Queer': [
            'queer', 'lgbtq', 'gay', 'lesbian', 'trans', 'transgender',
            'drag', 'pride', 'rainbow'
        ],
        'Kink / Adult': [
            'kink', 'bdsm', 'consent', 'dungeon', 'fetish', 'latex',
            'rope', 'bondage', 'dominance', 'submission'
        ],
        'Sober': [
            'sober', 'alcohol-free', 'substance-free', 'recovery',
            'sobriety', 'clean', 'non-alcoholic'
        ],
        'Family / Kids': [
            'family', 'kids', 'children', 'child', 'parent', 'toddler',
            'family-friendly', 'all ages'
        ],
        'Art': [
            'art', 'artist', 'paint', 'sculpture', 'gallery', 'creative',
            'drawing', 'installation', 'performance art'
        ],
        'Quiet / Contemplative': [
            'quiet', 'peaceful', 'calm', 'serene', 'contemplative',
            'silence', 'tranquil', 'sanctuary', 'refuge'
        ]
    }

    # Collect all text for each camp
    camp_texts = {}
    for camp_name, camp_data in history.items():
        texts = []
        for year_data in camp_data['history']:
            if year_data.get('description'):
                texts.append(year_data['description'])
            for event in year_data.get('events', []):
                texts.append(event.get('title', ''))
                texts.append(event.get('description', ''))
        camp_texts[camp_name] = ' '.join(texts)

    # Count camps matching each axis
    axis_results = {}
    for axis_name, keywords in axes.items():
        matching_camps = 0
        total_matches = 0
        keyword_dist = Counter()

        for camp_name, text in camp_texts.items():
            counts = extract_keywords(text, keywords)
            total_camp_matches = sum(counts.values())
            if total_camp_matches > 0:
                matching_camps += 1
                total_matches += total_camp_matches
                for kw, count in counts.items():
                    keyword_dist[kw] += count

        axis_results[axis_name] = {
            'matching_camps': matching_camps,
            'total_matches': total_matches,
            'keyword_dist': keyword_dist
        }

    # Print results sorted by prevalence
    print("Axes ranked by number of matching camps:\n")
    sorted_axes = sorted(axis_results.items(),
                         key=lambda x: x[1]['matching_camps'],
                         reverse=True)

    for axis_name, results in sorted_axes:
        pct = results['matching_camps'] / len(camp_texts) * 100
        print(f"{axis_name}:")
        print(f"  Camps: {results['matching_camps']}/{len(camp_texts)} ({pct:.1f}%)")
        print(f"  Total keyword matches: {results['total_matches']}")
        if results['keyword_dist']:
            top_keywords = results['keyword_dist'].most_common(5)
            print(f"  Top keywords: {', '.join(f'{kw} ({cnt})' for kw, cnt in top_keywords)}")
        print()


def analyze_event_types(history):
    """Analyze event type distribution"""
    print("=" * 80)
    print("EVENT TYPE DISTRIBUTION")
    print("=" * 80)

    event_types = Counter()
    for camp_name, camp_data in history.items():
        for year_data in camp_data['history']:
            for event in year_data.get('events', []):
                event_type = event.get('event_type', 'Unknown')
                event_types[event_type] += 1

    print(f"Total events: {sum(event_types.values()):,}")
    print(f"Unique event types: {len(event_types)}")
    print()
    print("Top event types:")
    for event_type, count in event_types.most_common(20):
        pct = count / sum(event_types.values()) * 100
        print(f"  {event_type}: {count:,} ({pct:.1f}%)")
    print()


def analyze_urls(camps, history):
    """Analyze URL availability"""
    print("=" * 80)
    print("URL AVAILABILITY")
    print("=" * 80)

    camps_with_urls = sum(1 for c in camps if c.get('url'))
    print(f"2025 camps with URLs: {camps_with_urls}/{len(camps)} ({camps_with_urls/len(camps)*100:.1f}%)")

    # Historical URLs
    total_year_records = 0
    year_records_with_urls = 0
    for camp_name, camp_data in history.items():
        for year_data in camp_data['history']:
            total_year_records += 1
            if year_data.get('url'):
                year_records_with_urls += 1

    print(f"Historical records with URLs: {year_records_with_urls}/{total_year_records} ({year_records_with_urls/total_year_records*100:.1f}%)")
    print()


def main():
    print("\nBRC CAMP DATA EXPLORATION")
    print("=" * 80)
    print()

    camps, history = load_data()

    analyze_basic_stats(camps, history)
    analyze_text_fields(camps, history)
    analyze_hometowns(camps)
    analyze_urls(camps, history)
    analyze_event_types(history)
    analyze_potential_axes(camps, history)

    print("=" * 80)
    print("EXPLORATION COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
