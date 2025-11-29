#!/usr/bin/env python3
"""
Download historical Burning Man camp or event data from the API.

Usage:
    python download_historical_camps.py camps YOUR_API_KEY
    python download_historical_camps.py events YOUR_API_KEY

Downloads data from 2025 backwards, skipping 2020-2021 (Covid years),
until the API returns an error indicating no more data is available.
"""

import sys
import json
import requests
import time
from pathlib import Path

BASE_URL = "https://api.burningman.org"
SKIP_YEARS = {2020, 2021}  # Covid years


def download_data(year, api_key, data_type):
    """
    Download camp or event data for a specific year.

    Args:
        year: The year to download data for
        api_key: The Burning Man API key
        data_type: Either 'camps' or 'events'

    Returns:
        Tuple of (success: bool, data: dict or None, error_message: str or None)
    """
    endpoint = "camp" if data_type == "camps" else "event"
    url = f"{BASE_URL}/api/{endpoint}?year={year}"
    headers = {
        "Accept": "application/json",
        "X-API-Key": api_key
    }

    print(f"Downloading {data_type} for {year}...", end=" ", flush=True)

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            count = len(data) if isinstance(data, list) else 'unknown'
            print(f"✓ Success ({count} {data_type})")
            return True, data, None
        else:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_detail = response.json()
                if isinstance(error_detail, dict) and 'message' in error_detail:
                    error_msg += f": {error_detail['message']}"
            except:
                pass
            print(f"✗ Failed ({error_msg})")
            return False, None, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        print(f"✗ Error ({error_msg})")
        return False, None, error_msg


def save_data(year, data, data_type):
    """
    Save camp or event data to a JSON file.

    Args:
        year: The year of the data
        data: The data to save
        data_type: Either 'camps' or 'events'
    """
    filename = f"{data_type}{year}.json"
    filepath = Path(__file__).parent / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  → Saved to {filename}")


def main():
    if len(sys.argv) != 3:
        print("Error: Data type and API key required")
        print(f"Usage: {sys.argv[0]} [camps|events] YOUR_API_KEY")
        sys.exit(1)

    data_type = sys.argv[1].lower()
    api_key = sys.argv[2]

    if data_type not in ['camps', 'events']:
        print("Error: Data type must be 'camps' or 'events'")
        print(f"Usage: {sys.argv[0]} [camps|events] YOUR_API_KEY")
        sys.exit(1)

    if not api_key or api_key.strip() == "":
        print("Error: API key cannot be empty")
        sys.exit(1)

    print("=" * 60)
    print(f"Burning Man Historical {data_type.capitalize()} Data Downloader")
    print("=" * 60)
    print()

    # Start from 2025 and go backwards
    year = 2025
    consecutive_failures = 0
    total_downloaded = 0

    while True:
        # Skip Covid years
        if year in SKIP_YEARS:
            print(f"Skipping {year} (Covid year)")
            year -= 1
            continue

        # Download data for this year
        success, data, error = download_data(year, api_key, data_type)

        if success:
            save_data(year, data, data_type)
            total_downloaded += 1
            consecutive_failures = 0

            # Brief pause to be nice to the API
            time.sleep(0.5)
        else:
            consecutive_failures += 1

            # If we get 2 consecutive failures, assume we've gone back far enough
            if consecutive_failures >= 2:
                print()
                print(f"Stopped at {year} after {consecutive_failures} consecutive failures.")
                print("Assuming no more historical data is available.")
                break

        # Move to the previous year
        year -= 1

        # Safety check - don't go before 2000
        if year < 2000:
            print()
            print("Reached year 2000, stopping.")
            break

    print()
    print("=" * 60)
    print(f"Download complete! Successfully downloaded {total_downloaded} years of data.")
    print("=" * 60)


if __name__ == "__main__":
    main()
