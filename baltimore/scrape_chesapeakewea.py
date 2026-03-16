from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo


CALENDAR_URL = "https://www.memberleap.com/members/calendar6c_responsive.php?org_id=CWEA"
ORG_URL = "https://www.chesapeakewea.org/"
DEFAULT_IMAGE_URL = "https://www.chesapeakewea.org/images/top-logo-new.svg"
TIMEZONE = ZoneInfo("America/New_York")


def _find_json_ld_event(html_text: str) -> Optional[Dict[str, object]]:
    for match in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html_text, re.DOTALL | re.IGNORECASE):
        raw_json = match.group(1).strip()
        if not raw_json:
            continue
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") == "Event":
                return candidate
    return None


def _iso_with_eastern(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=TIMEZONE).isoformat()


def _parse_detail(url: str, scraped_at: str) -> Optional[Dict[str, object]]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    payload = _find_json_ld_event(response.text)
    if not payload:
        return None

    description_panel = None
    location_panel = None
    for panel in soup.select("div.panel.panel-default"):
        title = panel.select_one("div.panel-title")
        if not title:
            continue
        heading = title.get_text(" ", strip=True)
        if heading == "Event Description":
            description_panel = panel.select_one("div.panel-body")
        elif heading == "Location":
            location_panel = panel.select_one("div.panel-body")

    image_tag = description_panel.find("img") if description_panel else None
    location_name = ""
    location_address = ""
    if isinstance(payload.get("Location"), dict):
        location_payload = payload["Location"]
        location_name = location_payload.get("name", "") or ""
        address_payload = location_payload.get("address", {}) or {}
        location_address = ", ".join(
            part.strip()
            for part in [
                address_payload.get("streetAddress", ""),
                address_payload.get("addressLocality", ""),
                address_payload.get("addressRegion", ""),
                address_payload.get("postalCode", ""),
            ]
            if part and part.strip()
        )

    if location_panel:
        location_text = " ".join(location_panel.stripped_strings)
        if location_text and not location_address:
            location_address = location_text

    return {
        "id": hashlib.md5(url.encode()).hexdigest()[:16],
        "name": payload.get("name", ""),
        "startDate": _iso_with_eastern(payload.get("startDate")),
        "endTime": _iso_with_eastern(payload.get("endDate")),
        "description": unescape(description_panel.get_text("\n", strip=True)) if description_panel else (payload.get("description", "") or ""),
        "url": url,
        "status": "ACTIVE",
        "location": {
            "name": location_name,
            "address": location_address,
        },
        "imageUrl": urljoin(url, image_tag.get("src", "")) if image_tag else DEFAULT_IMAGE_URL,
        "recurring": False,
        "scrapeTime": scraped_at,
    }


def scrape_events() -> List[Dict[str, object]]:
    response = requests.get(CALENDAR_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict[str, object]] = []
    seen_urls = set()

    for link in soup.select("div.cal-event-title a[href*='moreinfo.php']"):
        event_url = urljoin(CALENDAR_URL, link.get("href", ""))
        if not event_url or event_url in seen_urls:
            continue
        seen_urls.add(event_url)
        try:
            event = _parse_detail(event_url, scraped_at)
        except Exception as exc:
            print(f"Error fetching Chesapeake WEA event {event_url}: {exc}")
            continue
        if event:
            events.append(event)

    return events
