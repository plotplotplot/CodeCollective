import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://mpa.maryland.gov/Pages/port-commission.aspx"
BASE_URL = "https://mpa.maryland.gov"
TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
DEFAULT_DURATION = timedelta(hours=2)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}


def _clean(text):
    return " ".join((text or "").split()).strip()


def _parse_date_from_text_or_url(text, url):
    blob = f"{text} {url}"
    patterns = [
        (
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})",
            "%B %d %Y",
        ),
        (
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),\s*(\d{4})",
            "%b %d %Y",
        ),
    ]
    for pattern, date_fmt in patterns:
        match = re.search(pattern, blob, flags=re.IGNORECASE)
        if match:
            parsed = datetime.strptime(
                f"{match.group(1)} {int(match.group(2))} {int(match.group(3))}",
                date_fmt,
            )
            return parsed.replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=TIMEZONE)

    numeric = re.search(r"(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)", blob)
    if numeric:
        month, day, yy = map(int, numeric.groups())
        year = 2000 + yy
        try:
            return datetime(year, month, day, 9, 0, tzinfo=TIMEZONE)
        except ValueError:
            return None

    return None


def scrape_events():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"MPA Port Commission fetch error: {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    now = datetime.now(TIMEZONE)
    floor = now - timedelta(days=7)

    events = []
    seen = set()

    for link in soup.select("a[href]"):
        label = _clean(link.get_text(" ", strip=True))
        href = (link.get("href") or "").strip()
        if not href:
            continue
        lower_blob = f"{label} {href}".lower()
        if "agenda" not in lower_blob:
            continue
        if "/documents/port-commission/" not in lower_blob:
            continue

        start_dt = _parse_date_from_text_or_url(label, href)
        if not start_dt or start_dt < floor:
            continue
        end_dt = start_dt + DEFAULT_DURATION

        event_url = urljoin(BASE_URL, href)
        key = f"{start_dt.isoformat()}::{event_url}"
        if key in seen:
            continue
        seen.add(key)

        title_date = start_dt.strftime("%B %-d, %Y")
        events.append(
            {
                "name": f"Maryland Port Commission Meeting ({title_date})",
                "startDate": start_dt.isoformat(),
                "endDate": end_dt.isoformat(),
                "endTime": end_dt.isoformat(),
                "description": "Official Maryland Port Commission meeting agenda posting.",
                "url": event_url,
                "status": "ACTIVE",
                "location": {
                    "name": "Maryland Port Administration",
                    "address": "Maryland Port Administration, Baltimore, MD",
                    "city": "Baltimore",
                    "state": "MD",
                    "country": "US",
                },
                "imageUrl": "https://mpa.maryland.gov/_catalogs/masterpage/images/favicon.ico",
                "recurring": False,
            }
        )

    events.sort(key=lambda e: e.get("startDate", ""))
    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
