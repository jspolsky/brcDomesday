#!/usr/bin/env python3
"""
Data Shaping Pipeline for BRC Camp Recommendation Engine

Consolidates camp descriptions and events into clean, structured records
suitable for embedding generation and feature extraction.

Output: shaped_camps.json with canonical camp records
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any


def load_data():
    """Load camps and history data"""
    data_dir = Path(__file__).parent.parent / 'data'

    with open(data_dir / 'camps.json') as f:
        camps = json.load(f)

    with open(data_dir / 'campHistory.json') as f:
        history = json.load(f)

    return camps, history


def clean_text(text: str) -> str:
    """
    Clean and normalize text:
    - Remove extra whitespace
    - Normalize line breaks
    - Remove common boilerplate phrases
    - Strip URLs (keep them separate in structured data)
    """
    if not text:
        return ""

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Remove common boilerplate phrases
    boilerplate_patterns = [
        r'see (?:the )?playa events (?:app|guide)',
        r'check (?:the )?playa events (?:app|guide)',
        r'visit our camp for more info(?:rmation)?',
        r'come (?:visit|see) us at our camp',
        r'located at \d+:\d+',  # Location info (we have this structured)
    ]

    for pattern in boilerplate_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Clean up any double spaces created by removals
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def extract_year_range(history_records: List[Dict]) -> Dict[str, Any]:
    """Extract year range and attendance info from history"""
    if not history_records:
        return {'first_year': None, 'last_year': None, 'total_years': 0, 'years': []}

    years = sorted([record['year'] for record in history_records])

    return {
        'first_year': years[0],
        'last_year': years[-1],
        'total_years': len(years),
        'years': years
    }


def consolidate_descriptions(history_records: List[Dict]) -> Dict[str, str]:
    """
    Consolidate descriptions across years.

    Returns:
        - all_descriptions: concatenated with year markers
        - latest_description: most recent description
    """
    if not history_records:
        return {'all_descriptions': '', 'latest_description': ''}

    # Sort by year descending (most recent first)
    sorted_records = sorted(history_records, key=lambda x: x['year'], reverse=True)

    latest_description = clean_text(sorted_records[0].get('description', ''))

    # Concatenate all descriptions with year markers
    description_parts = []
    for record in sorted_records:
        desc = clean_text(record.get('description', ''))
        if desc:
            description_parts.append(f"[{record['year']}] {desc}")

    all_descriptions = ' '.join(description_parts)

    return {
        'all_descriptions': all_descriptions,
        'latest_description': latest_description
    }


def consolidate_events(history_records: List[Dict]) -> Dict[str, Any]:
    """
    Consolidate events across all years.

    Returns:
        - event_text: concatenated event titles and descriptions
        - event_count: total number of events
        - event_types: distribution of event types
        - recent_event_text: events from the most recent year only
    """
    all_events = []
    recent_events = []
    event_types = {}

    if not history_records:
        return {
            'event_text': '',
            'recent_event_text': '',
            'event_count': 0,
            'event_types': {}
        }

    # Sort by year descending
    sorted_records = sorted(history_records, key=lambda x: x['year'], reverse=True)
    most_recent_year = sorted_records[0]['year']

    for record in sorted_records:
        events = record.get('events', [])
        for event in events:
            title = clean_text(event.get('title', ''))
            description = clean_text(event.get('description', ''))
            event_type = event.get('event_type', 'Unknown')

            # Combine title and description
            event_text = f"{title}. {description}" if description else title

            if event_text:
                all_events.append(event_text)

                # Track events from most recent year
                if record['year'] == most_recent_year:
                    recent_events.append(event_text)

            # Count event types
            event_types[event_type] = event_types.get(event_type, 0) + 1

    return {
        'event_text': ' '.join(all_events),
        'recent_event_text': ' '.join(recent_events),
        'event_count': len(all_events),
        'event_types': event_types
    }


def create_shaped_record(camp: Dict, history_data: Dict) -> Dict[str, Any]:
    """
    Create a canonical shaped record for a camp.

    Combines current data with historical data into a clean structure.
    """
    camp_name = camp['name']
    history_records = history_data.get(camp_name, {}).get('history', [])

    # Extract temporal info
    year_info = extract_year_range(history_records)

    # Consolidate text
    descriptions = consolidate_descriptions(history_records)
    events = consolidate_events(history_records)

    # Create master text corpus (for embedding generation)
    # Weight: descriptions more heavily than individual events
    text_corpus_parts = []

    if descriptions['latest_description']:
        # Include latest description 2x for more weight
        text_corpus_parts.append(descriptions['latest_description'])
        text_corpus_parts.append(descriptions['latest_description'])

    if descriptions['all_descriptions']:
        text_corpus_parts.append(descriptions['all_descriptions'])

    if events['event_text']:
        text_corpus_parts.append(events['event_text'])

    text_corpus = ' '.join(text_corpus_parts)

    # Structured record
    shaped_record = {
        # Identity
        'uid': camp.get('uid'),
        'name': camp_name,
        'year': camp.get('year', 2025),

        # Geographic (can be messy - multiple locations, abbreviations, etc.)
        'hometown': (camp.get('hometown') or '').lower().strip(),
        'hometown_raw': camp.get('hometown'),  # Keep original for future cleanup

        # Temporal
        'years_active': year_info,

        # Contact/URLs
        'url': camp.get('url'),
        'contact_email': camp.get('contact_email'),

        # Location (2025)
        'location_string': camp.get('location_string'),
        'location': camp.get('location'),

        # Text corpora (for analysis)
        'text_corpus': text_corpus,  # Master corpus for embeddings
        'latest_description': descriptions['latest_description'],
        'all_descriptions': descriptions['all_descriptions'],
        'event_text': events['event_text'],
        'recent_event_text': events['recent_event_text'],

        # Event metadata
        'event_count': events['event_count'],
        'event_types': events['event_types'],

        # Images
        'images': camp.get('images', []),

        # Metadata
        'text_corpus_length': len(text_corpus),
        'has_events': events['event_count'] > 0,
        'has_description': len(descriptions['latest_description']) > 0,
    }

    return shaped_record


def shape_all_camps(camps: List[Dict], history: Dict) -> List[Dict]:
    """Process all camps through the shaping pipeline"""
    shaped_camps = []

    for camp in camps:
        shaped_record = create_shaped_record(camp, history)
        shaped_camps.append(shaped_record)

    return shaped_camps


def save_shaped_data(shaped_camps: List[Dict], output_path: Path):
    """Save shaped data to JSON file"""
    with open(output_path, 'w') as f:
        json.dump(shaped_camps, f, indent=2)

    print(f"Saved {len(shaped_camps)} shaped camp records to {output_path}")


def print_statistics(shaped_camps: List[Dict]):
    """Print statistics about the shaped data"""
    print("\n" + "=" * 80)
    print("DATA SHAPING STATISTICS")
    print("=" * 80)

    total_camps = len(shaped_camps)
    camps_with_descriptions = sum(1 for c in shaped_camps if c['has_description'])
    camps_with_events = sum(1 for c in shaped_camps if c['has_events'])

    total_text_length = sum(c['text_corpus_length'] for c in shaped_camps)
    avg_text_length = total_text_length / total_camps

    print(f"Total camps processed: {total_camps}")
    print(f"Camps with descriptions: {camps_with_descriptions} ({camps_with_descriptions/total_camps*100:.1f}%)")
    print(f"Camps with events: {camps_with_events} ({camps_with_events/total_camps*100:.1f}%)")
    print()
    print(f"Total text corpus: {total_text_length:,} characters")
    print(f"Average text per camp: {avg_text_length:.0f} characters")
    print()

    # Find camps with most/least text
    sorted_by_text = sorted(shaped_camps, key=lambda c: c['text_corpus_length'], reverse=True)

    print("Top 5 camps by text volume:")
    for camp in sorted_by_text[:5]:
        print(f"  {camp['name']}: {camp['text_corpus_length']:,} chars, {camp['event_count']} events")
    print()

    print("5 camps with least text:")
    for camp in sorted_by_text[-5:]:
        print(f"  {camp['name']}: {camp['text_corpus_length']:,} chars, {camp['event_count']} events")
    print()


def show_sample(shaped_camps: List[Dict], camp_name: str = None):
    """Show a sample shaped record for inspection"""
    print("=" * 80)
    print("SAMPLE SHAPED RECORD")
    print("=" * 80)

    # If no camp specified, pick one with good data
    if camp_name:
        sample = next((c for c in shaped_camps if c['name'] == camp_name), None)
    else:
        # Find a camp with lots of data
        sample = max(shaped_camps, key=lambda c: c['text_corpus_length'])

    if not sample:
        print("Camp not found!")
        return

    print(f"\nCamp: {sample['name']}")
    print(f"Hometown: {sample['hometown']}")
    print(f"Years active: {sample['years_active']['total_years']} "
          f"({sample['years_active']['first_year']}-{sample['years_active']['last_year']})")
    print(f"Events: {sample['event_count']}")
    print(f"Text corpus length: {sample['text_corpus_length']:,} chars")
    print()
    print("Latest description:")
    print(f"  {sample['latest_description'][:300]}...")
    print()
    print("Sample event text (first 300 chars):")
    print(f"  {sample['event_text'][:300]}...")
    print()
    print("Top event types:")
    sorted_types = sorted(sample['event_types'].items(), key=lambda x: x[1], reverse=True)
    for event_type, count in sorted_types[:5]:
        print(f"  {event_type}: {count}")
    print()


def main():
    print("\nBRC CAMP DATA SHAPING PIPELINE")
    print("=" * 80)
    print()

    # Load data
    print("Loading data...")
    camps, history = load_data()
    print(f"Loaded {len(camps)} camps and {len(history)} historical records")
    print()

    # Shape data
    print("Shaping data...")
    shaped_camps = shape_all_camps(camps, history)
    print("Shaping complete!")
    print()

    # Print statistics
    print_statistics(shaped_camps)

    # Show sample
    show_sample(shaped_camps)

    # Save shaped data
    output_path = Path(__file__).parent / 'shaped_camps.json'
    save_shaped_data(shaped_camps, output_path)

    print("=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"\nShaped data saved to: {output_path}")
    print("Ready for embedding generation and feature extraction!")
    print()


if __name__ == '__main__':
    main()
