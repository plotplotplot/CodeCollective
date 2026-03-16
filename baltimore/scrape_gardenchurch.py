from datetime import datetime, timedelta
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://www.thegardenbaltimore.com/"
DEFAULT_LOCATION = {
    "name": "The Garden Church",
    "address": "1500 Druid Hill Ave",
    "city": "Baltimore",
    "state": "MD",
    "country": "US",
}


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
    if "Morning Worship Service - 10:30AM" not in page_text:
        return []

    next_sunday = _next_sunday()
    definitions = [
        ("The Garden Church Sunday School", 9, 30, 60),
        ("The Garden Church Morning Worship Service", 10, 30, 90),
        ("The Garden Church Evening Prayer and Praise Service", 17, 0, 90),
    ]

    events: List[Dict] = []
    for name, hour, minute, duration_minutes in definitions:
        start_dt = next_sunday.replace(hour=hour, minute=minute, second=0, microsecond=0)
        events.append({
            "name": name,
            "description": "Recurring Sunday schedule published on The Garden Church homepage.",
            "startDate": start_dt.isoformat(),
            "endTime": (start_dt + timedelta(minutes=duration_minutes)).isoformat(),
            "url": url,
            "status": "ACTIVE",
            "location": dict(DEFAULT_LOCATION),
            "recurring": True,
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        })

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
