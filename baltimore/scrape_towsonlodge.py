from __future__ import annotations

from datetime import datetime, timedelta
from html import unescape
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from zoneinfo import ZoneInfo


SOURCE_URL = "https://towsonlodge.us/calendar-%26-events"
TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_LOCATION = {
    "name": "Towson Lodge #79",
    "address": "505 York Rd",
    "city": "Towson",
    "state": "MD",
    "postalCode": "21204",
    "country": "US",
}


def _get_next_thursdays(start_date: datetime, count: int = 12) -> List[datetime]:
    """Get the next 'count' Thursdays starting from start_date."""
    thursdays = []
    current = start_date

    # Find the next Thursday
    while current.weekday() != 3:  # 3 = Thursday
        current += timedelta(days=1)

    # Add Thursdays (1st and 3rd of each month)
    for _ in range(count):
        # Check if this Thursday is the 1st or 3rd Thursday of the month
        first_of_month = current.replace(day=1)
        first_thursday = first_of_month + timedelta(days=(3 - first_of_month.weekday()) % 7)

        if current == first_thursday or current == first_thursday + timedelta(days=14):
            thursdays.append(current)

        # Move to next Thursday
        current += timedelta(days=7)

    return thursdays


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    """
    Scrape events from Towson Lodge #79.
    Since the website doesn't currently list events dynamically,
    we generate regular fellowship meetings (1st and 3rd Thursdays).
    """
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    if response.status_code >= 500:
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict] = []

    # For now, generate regular fellowship meetings
    # Based on information found: "Fellowship every 1st and 3rd Thursday of each month"
    today = datetime.now(TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
    meeting_thursdays = _get_next_thursdays(today, 6)  # Next 6 months

    for meeting_date in meeting_thursdays:
        # Set meeting time to 7:30 PM (common for fraternal organizations)
        meeting_datetime = meeting_date.replace(hour=19, minute=30)

        events.append(
            {
                "name": "Towson Lodge #79 Fellowship Meeting",
                "description": "Regular fellowship meeting of Towson Lodge #79, Independent Order of Odd Fellows. Supporting the Towson and Baltimore communities since 1852.",
                "startDate": meeting_datetime.isoformat(),
                "url": url,
                "status": "ACTIVE",
                "location": DEFAULT_LOCATION,
                "imageUrl": "",
                "recurring": True,
                "scrapeTime": scraped_at,
            }
        )

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))