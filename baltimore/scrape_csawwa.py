from __future__ import annotations

import hashlib
import re
from datetime import datetime, time
from typing import Dict, List, Optional

import requests
from zoneinfo import ZoneInfo


HOME_URL = "https://www.csawwa.org/"
DEFAULT_IMAGE_URL = "https://nebula.wsimg.com/a352220abb2ce58ee293c6f787155331?AccessKeyId=4EEC3295F14ECD2E09A4&disposition=0&alloworigin=1"
TIMEZONE = ZoneInfo("America/New_York")
MONTH_LOOKUP = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def _build_iso(year: int, month_name: str, day: int, hour: int, minute: int) -> str:
    dt = datetime(year, MONTH_LOOKUP[month_name], day, hour, minute, tzinfo=TIMEZONE)
    return dt.isoformat()


def _make_event(name: str, start_iso: str, end_iso: str, url: str, description: str, location_name: str, location_address: str, scraped_at: str) -> Dict[str, object]:
    return {
        "id": hashlib.md5(f"{name}|{start_iso}|{url}".encode()).hexdigest()[:16],
        "name": name,
        "startDate": start_iso,
        "endTime": end_iso,
        "description": description,
        "url": url,
        "status": "ACTIVE",
        "location": {
            "name": location_name,
            "address": location_address,
        },
        "imageUrl": DEFAULT_IMAGE_URL,
        "recurring": False,
        "scrapeTime": scraped_at,
    }


def scrape_events() -> List[Dict[str, object]]:
    response = requests.get(HOME_URL, timeout=30)
    response.raise_for_status()
    html = response.text
    scraped_at = datetime.now(TIMEZONE).isoformat()
    current_year = datetime.now(TIMEZONE).year
    events: List[Dict[str, object]] = []

    ace_link_match = re.search(r"https://ace\.awwa\.org/?", html, re.IGNORECASE)
    if ace_link_match:
        events.append(
            _make_event(
                name="AWWA ACE26",
                start_iso=_build_iso(current_year, "June", 14, 0, 0),
                end_iso=_build_iso(current_year, "June", 17, 23, 59),
                url=ace_link_match.group(0),
                description="AWWA ACE26 in Washington, DC, hosted with Chesapeake and Virginia Sections.",
                location_name="Walter E. Washington Convention Center",
                location_address="Washington, DC",
                scraped_at=scraped_at,
            )
        )

    tri_match = re.search(r"September\s+1\s*-\s*4:.*?Tri-Association Conference,\s*Ocean City,\s*MD", html, re.IGNORECASE | re.DOTALL)
    if tri_match:
        events.append(
            _make_event(
                name="Tri-Association Conference",
                start_iso=_build_iso(current_year, "September", 1, 0, 0),
                end_iso=_build_iso(current_year, "September", 4, 23, 59),
                url=HOME_URL,
                description="CSAWWA-listed Tri-Association Conference in Ocean City, Maryland.",
                location_name="Ocean City",
                location_address="Ocean City, MD",
                scraped_at=scraped_at,
            )
        )

    return events
