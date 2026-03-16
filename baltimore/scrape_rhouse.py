from __future__ import annotations

from datetime import datetime
from html import unescape
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from zoneinfo import ZoneInfo


SOURCE_URL = "https://r.housebaltimore.com/"
TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_LOCATION = {
    "name": "R. House",
    "address": "301 W 29th St",
    "city": "Baltimore",
    "state": "MD",
    "postalCode": "21211",
    "country": "US",
}


def _parse_start(date_text: str) -> Optional[str]:
    normalized = " ".join(date_text.split()).replace("—", "-")
    if not normalized:
        return None

    start_part = normalized.split("-", 1)[0].strip()
    now = datetime.now(TIMEZONE)
    dt = parse(f"{start_part} {now.year}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TIMEZONE)
    return dt.isoformat()


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    section = soup.select_one("#current-pop-up")
    if not section:
        return []

    date_node = section.select_one("h6")
    title_node = section.select_one("h3")
    subtitle_node = section.select_one("h4")
    description_node = section.select_one("#current-pop-up-content p")
    image_node = section.select_one("#current-pop-up-image img")
    link_node = section.select_one("#popup-website-url")

    if not date_node or not title_node:
        return []

    start_iso = _parse_start(date_node.get_text(" ", strip=True))
    if not start_iso:
        return []

    description_parts = []
    if subtitle_node:
        description_parts.append(subtitle_node.get_text(" ", strip=True))
    if description_node:
        description_parts.append(description_node.get_text(" ", strip=True))

    return [
        {
            "name": unescape(title_node.get_text(" ", strip=True)),
            "description": "\n\n".join(part for part in description_parts if part),
            "startDate": start_iso,
            "url": link_node.get("href", url) if link_node else url,
            "status": "ACTIVE",
            "location": dict(DEFAULT_LOCATION),
            "imageUrl": image_node.get("src", "") if image_node else "",
            "recurring": False,
            "scrapeTime": datetime.now(TIMEZONE).isoformat(),
        }
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
