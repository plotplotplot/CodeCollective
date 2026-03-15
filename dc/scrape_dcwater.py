from __future__ import annotations

import hashlib
import re
from datetime import datetime
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo


BASE_URL = "https://www.dcwater.com"
CALENDAR_URL = f"{BASE_URL}/whats-going-on/event-calendar"
TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_IMAGE_URL = "https://www.dcwater.com/themes/custom/dcwater_theme/logo.svg"


def _parse_iso_utc(value: str) -> str:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(TIMEZONE).isoformat()


def _extract_event_links(page_html: str) -> List[str]:
    seen = set()
    links: List[str] = []
    for match in re.finditer(r'<a href="(/events/[^"]+)"[^>]*>(.*?)</a>', page_html, re.IGNORECASE | re.DOTALL):
        href = urljoin(BASE_URL, match.group(1))
        if href in seen:
            continue
        seen.add(href)
        links.append(href)
    return links


def _parse_detail(url: str, scraped_at: str) -> Optional[Dict[str, object]]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.select_one("h1.page-title, h2.node__title")
    when_tag = soup.select_one("div.field--name-field-event-date time.datetime")
    body_tag = soup.select_one("div.field--name-field-event-description")
    if body_tag is None:
        body_tag = soup.select_one("div.field--name-body")

    if not title_tag or not when_tag:
        return None

    start_iso = _parse_iso_utc(when_tag.get("datetime", ""))
    event_url = url
    name = title_tag.get_text(" ", strip=True)

    location_name = "DC Water"
    location_address = "Washington, DC"
    link_field = soup.select_one("div.field__item a[href]")
    if link_field and "watch-board-meetings" in link_field.get("href", ""):
        location_name = "DC Water Board Meeting Stream"

    return {
        "id": hashlib.md5(event_url.encode()).hexdigest()[:16],
        "name": name,
        "startDate": start_iso,
        "endTime": None,
        "description": unescape(body_tag.get_text("\n", strip=True)) if body_tag else "",
        "url": event_url,
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
    response = requests.get(CALENDAR_URL, timeout=30)
    response.raise_for_status()
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict[str, object]] = []

    for event_url in _extract_event_links(response.text):
        try:
            event = _parse_detail(event_url, scraped_at)
        except Exception as exc:
            print(f"Error fetching DC Water event {event_url}: {exc}")
            continue
        if event:
            events.append(event)

    return events
