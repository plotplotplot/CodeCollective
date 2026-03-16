from datetime import datetime, timedelta
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://calvaryec.com/events"
DEFAULT_IMAGE = "https://storage1.snappages.site/45TVJJ/assets/images/839853_4104x1688_500.jpg"
DEFAULT_LOCATION = {
    "name": "Calvary Chapel Ellicott City",
    "address": "9180 Rumsey Road",
    "city": "Columbia",
    "state": "MD",
    "postalCode": "21045",
    "country": "US",
}


def _next_weekday(target_weekday: int) -> datetime:
    now = datetime.now()
    days_ahead = (target_weekday - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return now + timedelta(days=days_ahead)


def _build_event(base_date: datetime, name: str, hour: int, minute: int, duration_minutes: int) -> Dict:
    start_dt = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return {
        "name": name,
        "description": "Recurring service time published on the Calvary Chapel Ellicott City events page.",
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
    if "Sunday Mornings" not in page_text or "Thursday  Evenings" not in page_text:
        return []

    next_sunday = _next_weekday(6)
    next_thursday = _next_weekday(3)

    return [
        _build_event(next_sunday, "Calvary Chapel Ellicott City Sunday Service", 8, 30, 90),
        _build_event(next_sunday, "Calvary Chapel Ellicott City Sunday Service", 10, 30, 90),
        _build_event(next_sunday, "Calvary Chapel Ellicott City Sunday Service", 12, 30, 90),
        _build_event(next_thursday, "Calvary Chapel Ellicott City Thursday Service", 19, 0, 90),
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
