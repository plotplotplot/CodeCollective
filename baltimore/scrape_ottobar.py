from __future__ import annotations

from datetime import datetime
from html import unescape
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from zoneinfo import ZoneInfo


SOURCE_URL = "https://theottobar.com/events/"
TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_LOCATION = {
    "name": "Ottobar",
    "address": "2549 N Howard St",
    "city": "Baltimore",
    "state": "MD",
    "postalCode": "21218",
    "country": "US",
}


def _parse_start(date_text: str, time_text: str) -> Optional[str]:
    normalized_date = " ".join(date_text.split())
    normalized_time = time_text.replace("Doors:", "").strip()
    if not normalized_date:
        return None

    if not normalized_time:
        dt = parse(normalized_date)
    else:
        dt = parse(f"{normalized_date} {normalized_time}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TIMEZONE)

    return dt.isoformat()


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    if response.status_code >= 500:
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict] = []

    for item in soup.select("div.eventWrapper.rhpSingleEvent"):
        title_link = item.select_one("a#eventTitle") or item.select_one("a.url")
        date_node = item.select_one("#eventDate")
        time_node = item.select_one(".eventDoorStartDate span")
        venue_link = item.select_one(".eventsVenueDiv .venueLink")
        image_node = item.select_one(".rhp-events-event-image img")

        if not title_link or not date_node:
            continue

        start_iso = _parse_start(
            date_node.get_text(" ", strip=True),
            time_node.get_text(" ", strip=True) if time_node else "",
        )
        if not start_iso:
            continue

        location = dict(DEFAULT_LOCATION)
        if venue_link:
            location["name"] = venue_link.get_text(" ", strip=True)

        events.append(
            {
                "name": unescape(title_link.get_text(" ", strip=True)),
                "description": "",
                "startDate": start_iso,
                "url": title_link.get("href", url),
                "status": "ACTIVE",
                "location": location,
                "imageUrl": image_node.get("src", "") if image_node else "",
                "recurring": False,
                "scrapeTime": scraped_at,
            }
        )

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
