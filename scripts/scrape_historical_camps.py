#!/usr/bin/env python3
"""
Scrape historical Burning Man camp data from the theme camp archive.

This script downloads camp information from 2014 back to 1997 from the
Burning Man website's historical archive, one page at a time with
respectful rate limiting (5 seconds between requests).

Usage:
    python scrape_historical_camps.py              # Scrape all years (2014-1997)
    python scrape_historical_camps.py 2004         # Scrape only 2004
    python scrape_historical_camps.py 2004 C       # Scrape only 2004, letter C
"""

import requests
import time
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

BASE_URL = "https://burningman.org/about/history/brc-history/theme-camp-archive/"
DELAY_BETWEEN_REQUESTS = 5  # seconds
LETTERS = ['#'] + [chr(i) for i in range(ord('A'), ord('Z') + 1)]  # #, A-Z


def fetch_page(year: int, letter: str) -> Optional[str]:
    """
    Fetch a single archive page for a given year and letter.

    Args:
        year: The year to fetch (1997-2014)
        letter: The first letter filter (# or A-Z)

    Returns:
        HTML content as string, or None if request fails
    """
    url = f"{BASE_URL}?yyyy={year}&ix={letter}"

    try:
        print(f"  Fetching {year} / {letter}...", end=" ", flush=True)

        headers = {
            'User-Agent': 'BRC-Domesday-Scraper/1.0 (Historical data collection; contact: see github.com/jspolsky/brcDomesday)'
        }

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            print(f"✓ ({len(response.content)} bytes)")
            return response.text
        else:
            print(f"✗ HTTP {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        return None


def parse_camp_data(html: str) -> List[Dict]:
    """
    Parse camp data from the HTML page.

    Args:
        html: HTML content of the archive page

    Returns:
        List of camp dictionaries
    """
    soup = BeautifulSoup(html, 'html.parser')
    camps = []

    # Look for divs with class 'newitem' - this is the container for each camp
    camp_divs = soup.find_all('div', class_='newitem')

    for camp_div in camp_divs:
        camp = extract_camp_from_newitem(camp_div)
        if camp:
            camps.append(camp)

    return camps


def extract_camp_from_newitem(camp_div) -> Optional[Dict]:
    """
    Extract camp data from a 'newitem' div element.

    Args:
        camp_div: BeautifulSoup div element with class 'newitem'

    Returns:
        Camp dictionary or None
    """
    camp = {}

    # Get camp name from h3 tag
    h3 = camp_div.find('h3')
    if h3:
        camp['name'] = h3.get_text(strip=True)
    else:
        return None  # No name, skip this camp

    # Get description from p tag with class 'excerpt'
    excerpt = camp_div.find('p', class_='excerpt')
    if excerpt:
        # Get the inner p tag if it exists, otherwise use the excerpt itself
        inner_p = excerpt.find('p')
        if inner_p:
            camp['description'] = inner_p.get_text(strip=True)
        else:
            camp['description'] = excerpt.get_text(strip=True)

    # Get email from span with class 'email'
    email_span = camp_div.find('span', class_='email')
    if email_span:
        email_link = email_span.find('a')
        if email_link and email_link.get('href', '').startswith('mailto:'):
            # Decode HTML entities in email
            camp['contact_email'] = email_link.get_text(strip=True)

    # Get hometown from span with class 'hometown'
    hometown_span = camp_div.find('span', class_='hometown')
    if hometown_span:
        # Remove the "Hometown:" label
        hometown_text = hometown_span.get_text(strip=True)
        if hometown_text.lower().startswith('hometown:'):
            camp['hometown'] = hometown_text.split(':', 1)[1].strip()
        else:
            camp['hometown'] = hometown_text

    # Get URL from span with class 'url'
    url_span = camp_div.find('span', class_='url')
    if url_span:
        url_link = url_span.find('a')
        if url_link:
            camp['url'] = url_link.get('href', '').strip()
        else:
            # Sometimes the URL is just text
            url_text = url_span.get_text(strip=True)
            if url_text.lower().startswith('url:'):
                camp['url'] = url_text.split(':', 1)[1].strip()
            else:
                camp['url'] = url_text

    # Get location from span with class 'location_string' (if it exists)
    location_span = camp_div.find('span', class_='location_string')
    if location_span:
        location_text = location_span.get_text(strip=True)
        if location_text.lower().startswith('location:'):
            camp['location_string'] = location_text.split(':', 1)[1].strip()
        else:
            camp['location_string'] = location_text

    return camp if 'name' in camp else None


def scrape_year(year: int) -> List[Dict]:
    """
    Scrape all camp data for a specific year.

    Args:
        year: The year to scrape (1997-2014)

    Returns:
        List of all camps for that year
    """
    print(f"\nScraping {year}...")
    all_camps = []

    for letter in LETTERS:
        # Fetch the page
        html = fetch_page(year, letter)

        if html:
            # Parse camp data
            camps = parse_camp_data(html)

            # Add year to each camp
            for camp in camps:
                camp['year'] = year

            all_camps.extend(camps)

            if camps:
                print(f"    Found {len(camps)} camp(s)")

        # Rate limiting - wait between requests
        if letter != LETTERS[-1]:  # Don't wait after last letter
            time.sleep(DELAY_BETWEEN_REQUESTS)

    return all_camps


def save_camps(year: int, camps: List[Dict]):
    """
    Save camps to a JSON file.

    Args:
        year: The year
        camps: List of camp dictionaries
    """
    # Add year field to each camp
    for camp in camps:
        camp['year'] = year
        # Add uid if not present (use name-based id)
        if 'uid' not in camp:
            camp['uid'] = f"scraped_{year}_{camp['name'].lower().replace(' ', '_')}"

    filename = f"camps{year}.json"
    filepath = Path(__file__).parent / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(camps, f, indent=2, ensure_ascii=False)

    print(f"  → Saved {len(camps)} camps to {filename}")


def scrape_single_page(year: int, letter: str):
    """
    Test mode: scrape a single page and display the results.

    Args:
        year: The year to scrape
        letter: The letter to scrape
    """
    print("=" * 70)
    print("Burning Man Historical Camp Data Scraper - TEST MODE")
    print("=" * 70)
    print(f"\nTesting single page: {year} / {letter}")
    print()

    html = fetch_page(year, letter)

    if html:
        camps = parse_camp_data(html)

        # Add year to each camp
        for camp in camps:
            camp['year'] = year

        print(f"\n{'=' * 70}")
        print(f"Results: Found {len(camps)} camp(s)")
        print('=' * 70)

        for i, camp in enumerate(camps, 1):
            print(f"\nCamp {i}:")
            print(json.dumps(camp, indent=2, ensure_ascii=False))

        # Ask if user wants to save
        print(f"\n{'=' * 70}")
        response = input(f"Save these {len(camps)} camps to camps{year}.json? (y/n): ")
        if response.lower() == 'y':
            save_camps(year, camps)
            print("Saved!")
        else:
            print("Not saved.")
    else:
        print("Failed to fetch page.")


def main():
    """
    Main scraping function.
    """
    # Parse command-line arguments
    test_year = None
    test_letter = None

    if len(sys.argv) >= 2:
        try:
            test_year = int(sys.argv[1])
            if test_year < 1997 or test_year > 2014:
                print(f"Error: Year must be between 1997 and 2014")
                sys.exit(1)
        except ValueError:
            print(f"Error: Invalid year '{sys.argv[1]}'")
            sys.exit(1)

    if len(sys.argv) >= 3:
        test_letter = sys.argv[2].upper()
        if test_letter not in LETTERS:
            print(f"Error: Letter must be # or A-Z")
            sys.exit(1)

    # Test mode: single page
    if test_year and test_letter:
        scrape_single_page(test_year, test_letter)
        return

    # Test mode: single year
    if test_year:
        print("=" * 70)
        print("Burning Man Historical Camp Data Scraper - SINGLE YEAR MODE")
        print("=" * 70)
        print(f"\nRate limit: {DELAY_BETWEEN_REQUESTS} seconds between requests")
        print(f"Year: {test_year}")
        print()

        camps = scrape_year(test_year)

        if camps:
            save_camps(test_year, camps)
            print(f"✓ Completed {test_year}: {len(camps)} camps total\n")
        else:
            print(f"✗ No camps found for {test_year}\n")

        return

    # Full mode: all years
    print("=" * 70)
    print("Burning Man Historical Camp Data Scraper - FULL MODE")
    print("=" * 70)
    print(f"\nRate limit: {DELAY_BETWEEN_REQUESTS} seconds between requests")
    print("Years: 2014 to 1997")
    print()

    response = input("This will take ~40 minutes. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Scrape from 2014 backwards to 1997
    for year in range(2014, 1996, -1):
        camps = scrape_year(year)

        if camps:
            save_camps(year, camps)
            print(f"✓ Completed {year}: {len(camps)} camps total\n")
        else:
            print(f"✗ No camps found for {year}\n")

        # Extra delay between years
        if year > 1997:
            print(f"Waiting before next year...\n")
            time.sleep(DELAY_BETWEEN_REQUESTS)

    print("=" * 70)
    print("Scraping complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
