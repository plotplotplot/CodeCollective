from datetime import datetime, timedelta
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://saintmos.org/gatherings"
DEFAULT_IMAGE = "https://saintmos.org/sites/saintmos.ryankavalsky.com/files/images/Saint%20Moses%20Church%20Logo.jpg"
DEFAULT_LOCATION = {
    "name": "St. Moses Church",
    "address": "400 E. 31st St",
    "city": "Baltimore",
    "state": "MD",
    "postalCode": "21218",
    "country": "US",
}


def _next_weekday(target_weekday: int) -> datetime:
    now = datetime.now()
    days_ahead = (target_weekday - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return now + timedelta(days=days_ahead)


def _build_event(base_date: datetime, name: str, hour: int, minute: int, description: str) -> Dict:
    start_dt = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    end_dt = start_dt + timedelta(minutes=75)
    return {
        "name": name,
        "description": description,
        "startDate": start_dt.isoformat(),
        "endTime": end_dt.isoformat(),
        "url": SOURCE_URL,
        "status": "ACTIVE",
        "location": dict(DEFAULT_LOCATION),
        "imageUrl": DEFAULT_IMAGE,
        "recurring": True,
        "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
    }


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    if "Sunday Gatherings" not in page_text:
        return []

    next_sunday = _next_weekday(6)
    description = (
        "Join St. Moses each Sunday in person or online. "
        "The gatherings page lists Sunday gatherings at 9:00 AM and 10:45 AM, "
        "with YouTube Live available for the morning gathering."
    )

    return [
        _build_event(next_sunday, "St. Moses Sunday Gathering", 9, 0, description),
        _build_event(next_sunday, "St. Moses Sunday Gathering", 10, 45, description),
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
