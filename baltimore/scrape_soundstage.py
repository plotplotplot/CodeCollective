from __future__ import annotations

from datetime import datetime
from html import unescape
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from zoneinfo import ZoneInfo


SOURCE_URL = "https://www.baltimoresoundstage.com/events-feed/"
TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_LOCATION = {
    "name": "Baltimore Soundstage",
    "address": "124 Market Pl",
    "city": "Baltimore",
    "state": "MD",
    "postalCode": "21202",
    "country": "US",
}


def _parse_start(date_text: str, time_text: str) -> Optional[str]:
    normalized_date = " ".join(date_text.split())
    normalized_time = ""
    if "Show Time |" in time_text:
        normalized_time = time_text.split("Show Time |", 1)[1].strip()
    elif "Doors |" in time_text:
        normalized_time = time_text.split("Doors |", 1)[1].split("//", 1)[0].strip()

    if not normalized_date:
        return None

    dt = parse(f"{normalized_date} {normalized_time}") if normalized_time else parse(normalized_date)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TIMEZONE)
    return dt.isoformat()


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict] = []

    for article in soup.select("article.event"):
        title_link = article.select_one("h2 a")
        date_node = article.select_one(".event-date")
        time_node = article.select_one(".event-time")
        presented_by = article.select_one(".presented-by")
        title_node = article.select_one(".title")
        supporting_node = article.select_one(".supporting-acts")
        image_node = article.select_one(".event-thumb-link img")

        if not title_link or not date_node:
            continue

        start_iso = _parse_start(
            date_node.get_text(" ", strip=True),
            time_node.get_text(" ", strip=True) if time_node else "",
        )
        if not start_iso:
            continue

        title_parts = []
        if presented_by:
            title_parts.append(presented_by.get_text(" ", strip=True))
        if title_node:
            title_parts.append(title_node.get_text(" ", strip=True))
        if supporting_node:
            title_parts.append(supporting_node.get_text(" ", strip=True))

        events.append(
            {
                "name": unescape(" - ".join(part for part in title_parts if part) or title_link.get_text(" ", strip=True)),
                "description": time_node.get_text(" ", strip=True) if time_node else "",
                "startDate": start_iso,
                "url": title_link.get("href", url),
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
