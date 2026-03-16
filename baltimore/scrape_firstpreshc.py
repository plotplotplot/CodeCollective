from datetime import datetime, timedelta
from typing import Dict, List

import requests


SOURCE_URL = "https://www.firstpreshc.org/worship"
DEFAULT_IMAGE = "https://i.ytimg.com/vi/emDHyQ44pTI/maxresdefault.jpg"
DEFAULT_LOCATION = {
    "name": "First Presbyterian Church of Howard County",
    "city": "Columbia",
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

    if "10:30a Worship Service" not in response.text and "Worship Services" not in response.text:
        return []

    start_dt = _next_sunday().replace(hour=10, minute=30, second=0, microsecond=0)
    end_dt = start_dt + timedelta(minutes=90)
    return [{
        "name": "First Presbyterian Church of Howard County Sunday Worship",
        "description": "Recurring Sunday worship service published on the church worship page.",
        "startDate": start_dt.isoformat(),
        "endTime": end_dt.isoformat(),
        "url": url,
        "status": "ACTIVE",
        "location": dict(DEFAULT_LOCATION),
        "imageUrl": DEFAULT_IMAGE,
        "recurring": True,
        "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
    }]


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
