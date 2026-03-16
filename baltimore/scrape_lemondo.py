from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo


SOURCE_URL = "https://www.lemondo.org/"
BASE_URL = "https://www.lemondo.org"
TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_LOCATION = {
    "name": "Le Mondo",
    "address": "406 N Howard St",
    "city": "Baltimore",
    "state": "MD",
    "postalCode": "21201",
    "country": "US",
}


def _extract_dates_map(html: str) -> Dict[str, str]:
    dates: Dict[str, str] = {}
    pattern = re.compile(
        r'"([0-9a-f-]{36})":\{"utcOffset":[^}]*?"startDateISOFormatNotUTC":"([^"]+)"',
        re.IGNORECASE,
    )
    for event_id, start_iso in pattern.findall(html):
        dates[event_id] = start_iso
    return dates


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()

    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    dates_by_id = _extract_dates_map(html)
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict] = []

    for card in soup.select('li[data-hook="events-card"]'):
        title_link = card.select_one('a[data-hook="title"]')
        ticket_link = card.select_one('a[data-hook="ev-rsvp-button"]')
        image_node = card.select_one("img")
        more_info = card.select_one('button[data-hook^="more-info-link-"]')

        if not title_link or not more_info:
            continue

        event_id = more_info.get("data-hook", "").removeprefix("more-info-link-")
        start_iso = dates_by_id.get(event_id)
        if not start_iso:
            continue

        event_url = ticket_link.get("href") if ticket_link else title_link.get("href", "")
        event_url = urljoin(BASE_URL, event_url)

        events.append(
            {
                "name": unescape(title_link.get_text(" ", strip=True)),
                "description": "",
                "startDate": start_iso,
                "url": event_url,
                "status": "ACTIVE",
                "location": dict(DEFAULT_LOCATION),
                "imageUrl": image_node.get("src", "") if image_node else "",
                "recurring": False,
                "scrapeTime": scraped_at,
            }
        )

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
