#!/usr/bin/env python3
"""
Download historical Burning Man camp data from the API.

Usage:
    python download_historical_camps.py YOUR_API_KEY

Downloads camp data from 2025 backwards, skipping 2020-2021 (Covid years),
until the API returns an error indicating no more data is available.
"""

import sys
import json
import requests
import time
from pathlib import Path

BASE_URL = "https://api.burningman.org"
SKIP_YEARS = {2020, 2021}  # Covid years


def download_camp_data(year, api_key):
    """
    Download camp data for a specific year.

    Args:
        year: The year to download data for
        api_key: The Burning Man API key

    Returns:
        Tuple of (success: bool, data: dict or None, error_message: str or None)
    """
    url = f"{BASE_URL}/api/camp?year={year}"
    headers = {
        "Accept": "application/json",
        "X-API-Key": api_key
    }

    print(f"Downloading data for {year}...", end=" ", flush=True)

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success ({len(data) if isinstance(data, list) else 'unknown'} camps)")
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


def save_camp_data(year, data):
    """
    Save camp data to a JSON file.

    Args:
        year: The year of the data
        data: The camp data to save
    """
    filename = f"camps{year}.json"
    filepath = Path(__file__).parent / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  → Saved to {filename}")


def main():
    if len(sys.argv) != 2:
        print("Error: API key required")
        print(f"Usage: {sys.argv[0]} YOUR_API_KEY")
        sys.exit(1)

    api_key = sys.argv[1]

    if not api_key or api_key.strip() == "":
        print("Error: API key cannot be empty")
        sys.exit(1)

    print("=" * 60)
    print("Burning Man Historical Camp Data Downloader")
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
        success, data, error = download_camp_data(year, api_key)

        if success:
            save_camp_data(year, data)
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
