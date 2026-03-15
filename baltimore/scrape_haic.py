from datetime import datetime, timedelta
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://haicbaltimore.org/upcoming-events/"
DEFAULT_IMAGE = "https://haicbaltimore.org/wp-content/uploads/2019/01/home-page_03.png"
DEFAULT_LOCATION = {
    "name": "Hasbuna Allahu Islamic & Community Center",
    "address": "5100 Edmondson Ave",
    "city": "Baltimore",
    "state": "MD",
    "postalCode": "21229",
    "country": "US",
}


def _last_weekday_of_month(year: int, month: int, target_weekday: int) -> datetime:
    if month == 12:
        current = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        current = datetime(year, month + 1, 1) - timedelta(days=1)
    while current.weekday() != target_weekday:
        current -= timedelta(days=1)
    return current


def _nth_weekday_of_month(year: int, month: int, target_weekday: int, ordinal: int) -> datetime:
    current = datetime(year, month, 1)
    while current.weekday() != target_weekday:
        current += timedelta(days=1)
    current += timedelta(days=7 * (ordinal - 1))
    return current


def _next_occurrence(builder) -> datetime:
    now = datetime.now()
    for month_offset in range(0, 14):
        year = now.year + ((now.month - 1 + month_offset) // 12)
        month = ((now.month - 1 + month_offset) % 12) + 1
        candidate = builder(year, month)
        if candidate.date() >= now.date():
            return candidate
    raise RuntimeError("Could not compute next recurring date")


def _build_event(name: str, start_dt: datetime, duration_hours: int, description: str) -> Dict:
    end_dt = start_dt + timedelta(hours=duration_hours)
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
    upcoming = soup.select_one(".upcoming")
    if not upcoming:
        return []

    schedule_text = upcoming.get_text("\n", strip=True)
    events: List[Dict] = []

    if "Monthly Tahajjud" in schedule_text:
        start_dt = _next_occurrence(lambda year, month: _last_weekday_of_month(year, month, 4).replace(hour=22))
        events.append(
            _build_event(
                "HAIC Monthly Tahajjud",
                start_dt,
                2,
                "Recurring mosque prayer gathering listed on the HAIC upcoming events schedule as the last Friday of each month.",
            )
        )

    if "Monthly Quranic Recitation" in schedule_text:
        start_dt = _next_occurrence(lambda year, month: _last_weekday_of_month(year, month, 6).replace(hour=13))
        events.append(
            _build_event(
                "HAIC Monthly Quranic Recitation",
                start_dt,
                2,
                "Recurring mosque program listed on the HAIC upcoming events schedule as the last Sunday of each month.",
            )
        )

    if "Couples Lecture and Prayer" in schedule_text:
        start_dt = _next_occurrence(lambda year, month: _nth_weekday_of_month(year, month, 5, 2).replace(hour=18))
        events.append(
            _build_event(
                "HAIC Couples Lecture and Prayer",
                start_dt,
                2,
                "Recurring mosque event listed on the HAIC upcoming events schedule as the second Saturday of every month.",
            )
        )

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
