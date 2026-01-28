from datetime import datetime
from dateutil.tz import gettz

import csv
import json
import os

dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(dir, '../..', 'data')


def get_datetime() -> str:
    """Get current timestamp for logging."""
    NYC = gettz('America/New_York')
    now = datetime.now().astimezone(NYC)
    date_now = now.strftime('%b %d, %Y')
    time_now = now.strftime('%I:%M %p')
    return f'[{date_now} - {time_now}]'


def get_area_map() -> dict[str, str]:
    """Load StreetEasy's area name and ID mapping."""
    with open(os.path.join(dir, 'data/areas.json'), 'r') as f:
        areas = json.load(f)
    return {area['name']: area['id'] for area in areas}


def build_url(**kwargs) -> str:
    """Construct search URL based on input parameters."""
    q = '|'.join([f'{k}:{v}' for k, v in kwargs.items()])
    return f'https://streeteasy.com/for-rent/nyc/{q}?sort_by=listed_desc'


def export_to_csv(listings: list[dict], filename: str = None) -> str:
    """Export listings to a CSV file.

    Args:
        listings: List of listing dictionaries
        filename: Optional custom filename. Defaults to listings_YYYYMMDD_HHMMSS.csv

    Returns:
        Path to the exported CSV file
    """
    if not listings:
        return None

    os.makedirs(data_dir, exist_ok=True)

    if not filename:
        NYC = gettz('America/New_York')
        timestamp = datetime.now().astimezone(NYC).strftime('%Y%m%d_%H%M%S')
        filename = f'listings_{timestamp}.csv'

    filepath = os.path.join(data_dir, filename)

    fieldnames = ['address', 'neighborhood', 'price', 'url', 'listing_id']

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(listings)

    return filepath
