import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://www.baltimoreportalliance.org/career-expo/2026-highlights"
BASE_URL = "https://www.baltimoreportalliance.org"
TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}


def _clean(text):
    return " ".join((text or "").split()).strip()


def _extract_date(text):
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    parsed = datetime.strptime(
        f"{match.group(1)} {int(match.group(2))} {int(match.group(3))}",
        "%B %d %Y",
    )
    return parsed.replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=TIMEZONE)


def scrape_events():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Baltimore Port Alliance fetch error: {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    text = _clean(soup.get_text(" ", strip=True))
    start_dt = _extract_date(text)
    if not start_dt:
        return []

    end_dt = start_dt + timedelta(hours=4)
    page_title = _clean(soup.title.get_text()) if soup.title else "Baltimore Port Alliance Career Expo"
    event_name = "Baltimore Port Alliance Career Expo"
    if "2026" in page_title and "2026" not in event_name:
        event_name = f"{event_name} 2026"

    description = (
        "Baltimore Port Alliance career expo highlights and related workforce event details."
    )

    return [
        {
            "name": event_name,
            "startDate": start_dt.isoformat(),
            "endDate": end_dt.isoformat(),
            "endTime": end_dt.isoformat(),
            "description": description,
            "url": urljoin(BASE_URL, "/career-expo/2026-highlights"),
            "status": "ACTIVE",
            "location": {
                "name": "Baltimore Port Alliance",
                "address": "Baltimore, MD",
                "city": "Baltimore",
                "state": "MD",
                "country": "US",
            },
            "imageUrl": "",
            "recurring": False,
        }
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
