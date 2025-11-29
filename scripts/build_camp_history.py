#!/usr/bin/env python3
"""
Build campHistory.json from historical camp data files.

This script reads camps2025.json and all historical camp files (camps2024.json,
camps2023.json, etc.) and creates a consolidated history file showing which years
each 2025 camp has attended Burning Man.

Usage:
    python build_camp_history.py
"""

import json
from pathlib import Path
from collections import defaultdict


def load_camp_data(year):
    """
    Load camp data for a specific year.

    Args:
        year: The year to load

    Returns:
        List of camp objects, or None if file doesn't exist
    """
    filepath = Path(__file__).parent / f"camps{year}.json"

    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None


def load_event_data(year):
    """
    Load event data for a specific year.

    Args:
        year: The year to load

    Returns:
        List of event objects, or None if file doesn't exist
    """
    filepath = Path(__file__).parent / f"events{year}.json"

    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None


def extract_event_info(event):
    """
    Extract the relevant fields from an event object.

    Args:
        event: Event object from the JSON data

    Returns:
        Dictionary with title, description, and event_type label
    """
    event_type = event.get("event_type", {})
    return {
        "title": event.get("title", ""),
        "description": event.get("description", ""),
        "event_type": event_type.get("label") if event_type else None
    }


def extract_history_entry(camp, events_by_camp_uid=None):
    """
    Extract the relevant fields from a camp object for the history array.

    Args:
        camp: Camp object from the JSON data
        events_by_camp_uid: Dictionary mapping camp UIDs to lists of events (optional)

    Returns:
        Dictionary with year, uid, description, location_string, url, and events
    """
    camp_uid = camp.get("uid")
    events = []

    # If we have event data, find events for this camp
    if events_by_camp_uid and camp_uid and camp_uid in events_by_camp_uid:
        # Extract event info and deduplicate by title
        seen_titles = set()
        for event in events_by_camp_uid[camp_uid]:
            event_title = event.get("title", "")
            if event_title and event_title not in seen_titles:
                seen_titles.add(event_title)
                events.append(extract_event_info(event))

    return {
        "year": camp.get("year"),
        "uid": camp_uid,
        "description": camp.get("description", ""),
        "location_string": camp.get("location_string", ""),
        "url": camp.get("url"),
        "events": events
    }


def build_camp_history():
    """
    Build the campHistory.json file from all available historical data.
    """
    print("=" * 60)
    print("Building Camp History Database")
    print("=" * 60)
    print()

    # Load 2025 camps (our baseline)
    print("Loading 2025 camps...", end=" ")
    camps_2025 = load_camp_data(2025)

    if not camps_2025:
        print("✗ Failed")
        print("Error: Could not load camps2025.json")
        return

    print(f"✓ Loaded {len(camps_2025)} camps")

    # Load 2025 events
    print("Loading 2025 events...", end=" ")
    events_2025 = load_event_data(2025)

    if events_2025:
        print(f"✓ Loaded {len(events_2025)} events")
        # Build lookup dictionary: camp_uid -> list of events
        events_by_camp_uid_2025 = defaultdict(list)
        for event in events_2025:
            camp_uid = event.get("hosted_by_camp")
            if camp_uid:
                events_by_camp_uid_2025[camp_uid].append(event)
    else:
        print("✗ No event data available")
        events_by_camp_uid_2025 = {}

    # Build a set of all 2025 camp names
    camps_2025_names = {camp["name"] for camp in camps_2025}

    # Initialize the history dictionary
    camp_history = {}

    for camp in camps_2025:
        name = camp["name"]
        camp_history[name] = {
            "name": name,
            "history": [extract_history_entry(camp, events_by_camp_uid_2025)]
        }

    print()
    print("Loading historical data:")

    # Define the years to check (backwards from 2024, skipping 2020-2021)
    years_to_check = []
    for year in range(2024, 1996, -1):  # Go back to 1997
        if year not in {2020, 2021}:  # Skip Covid years
            years_to_check.append(year)

    total_matches = 0

    # Process each historical year
    for year in years_to_check:
        historical_camps = load_camp_data(year)

        if not historical_camps:
            print(f"  {year}: No camp data available, stopping here")
            break

        # Load events for this year
        historical_events = load_event_data(year)
        events_by_camp_uid = {}

        if historical_events:
            # Build lookup dictionary: camp_uid -> list of events
            events_by_camp_uid = defaultdict(list)
            for event in historical_events:
                camp_uid = event.get("hosted_by_camp")
                if camp_uid:
                    events_by_camp_uid[camp_uid].append(event)

        # Build a lookup dictionary by camp name for this year
        camps_by_name = {camp["name"]: camp for camp in historical_camps}

        # Find matches with 2025 camps
        matches = 0
        for camp_name in camps_2025_names:
            if camp_name in camps_by_name:
                historical_camp = camps_by_name[camp_name]
                camp_history[camp_name]["history"].append(
                    extract_history_entry(historical_camp, events_by_camp_uid)
                )
                matches += 1

        total_matches += matches
        event_info = f", {len(historical_events)} events" if historical_events else ""
        print(f"  {year}: {len(historical_camps)} camps{event_info}, {matches} matches with 2025")

    print()
    print("Sorting history entries by year...")

    # Sort each camp's history by year (descending)
    for camp_name in camp_history:
        camp_history[camp_name]["history"].sort(
            key=lambda x: x["year"],
            reverse=True
        )

    # Calculate statistics
    camps_with_history = sum(1 for camp in camp_history.values() if len(camp["history"]) > 1)

    print()
    print("Statistics:")
    print(f"  Total 2025 camps: {len(camp_history)}")
    print(f"  Camps with historical data: {camps_with_history}")
    print(f"  First-time camps: {len(camp_history) - camps_with_history}")
    print(f"  Total historical matches: {total_matches}")

    # Save the result
    output_path = Path(__file__).parent / "campHistory.json"

    print()
    print(f"Writing {output_path}...", end=" ")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(camp_history, f, indent=2, ensure_ascii=False)

    # Get file size
    file_size = output_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    print(f"✓ Done ({file_size_mb:.2f} MB)")

    print()
    print("=" * 60)
    print("Camp history database built successfully!")
    print("=" * 60)


def main():
    try:
        build_camp_history()
    except Exception as e:
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
