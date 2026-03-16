from datetime import datetime, timedelta
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://bridgeway.cc/services"
DEFAULT_IMAGE = "https://media.thechurchcoassets.com/accounts/6892/a4f26eec-2bd5-4c00-ae8e-2d898cbb17f3-imported-asset__largepreview__.webp"
CAMPUSES = [
    {
        "name": "Bridgeway Community Church Columbia Campus Sunday Service",
        "hour": 9,
        "minute": 0,
        "location": {
            "name": "Bridgeway Community Church Columbia Campus",
            "city": "Columbia",
            "state": "MD",
            "country": "US",
        },
    },
    {
        "name": "Bridgeway Community Church Owings Mills / Reisterstown Sunday Service",
        "hour": 10,
        "minute": 30,
        "location": {
            "name": "Bridgeway Community Church Owings Mills / Reisterstown Campus",
            "address": "11301 Red Run Blvd",
            "city": "Owings Mills",
            "state": "MD",
            "postalCode": "21117",
            "country": "US",
        },
    },
    {
        "name": "Bridgeway Community Church Columbia Campus Sunday Service",
        "hour": 11,
        "minute": 0,
        "location": {
            "name": "Bridgeway Community Church Columbia Campus",
            "city": "Columbia",
            "state": "MD",
            "country": "US",
        },
    },
]


def _next_sunday() -> datetime:
    now = datetime.now()
    days_ahead = (6 - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return now + timedelta(days=days_ahead)


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    if "Sunday Church Service Times" not in page_text or "Owings Mills/ Reisterstown Campus" not in page_text:
        return []

    next_sunday = _next_sunday()
    events: List[Dict] = []
    for campus in CAMPUSES:
        start_dt = next_sunday.replace(
            hour=campus["hour"],
            minute=campus["minute"],
            second=0,
            microsecond=0,
        )
        event: Dict = {
            "name": campus["name"],
            "description": "Recurring Sunday service time published on the Bridgeway services page.",
            "startDate": start_dt.isoformat(),
            "endTime": (start_dt + timedelta(minutes=90)).isoformat(),
            "url": url,
            "status": "ACTIVE",
            "location": dict(campus["location"]),
            "imageUrl": DEFAULT_IMAGE,
            "recurring": True,
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        }
        events.append(event)

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
