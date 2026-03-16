from __future__ import annotations

import json
from datetime import datetime
from html import unescape
from typing import Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from zoneinfo import ZoneInfo


SITEMAP_URL = "https://powerplantlive.com/sitemap.xml"
SOURCE_URL = "https://powerplantlive.com/events-and-entertainment/events"
TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_LOCATION = {
    "name": "Power Plant Live!",
    "address": "34 Market Place",
    "city": "Baltimore",
    "state": "MD",
    "postalCode": "21202",
    "country": "US",
}


def _event_urls_from_sitemap() -> List[str]:
    response = requests.get(SITEMAP_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "xml")
    urls: List[str] = []
    for loc in soup.find_all("loc"):
        url = loc.get_text(strip=True)
        path = urlparse(url).path.lower()
        if "/events-and-entertainment/events/" not in path:
            continue
        if path.endswith("/events") or "/past-events/" in path:
            continue
        urls.append(url)
    return urls


def _extract_event_payload(soup: BeautifulSoup) -> Dict:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        payloads = payload if isinstance(payload, list) else [payload]
        for item in payloads:
            if isinstance(item, dict) and item.get("@type") == "Event":
                return item
    return {}


def scrape_events(source_url: str = SOURCE_URL) -> List[Dict]:
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict] = []

    for event_url in _event_urls_from_sitemap():
        response = requests.get(event_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        payload = _extract_event_payload(soup)
        if not payload:
            continue

        start_text = payload.get("startDate")
        if not start_text:
            continue

        try:
            start_dt = parse(start_text)
        except Exception:
            continue
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=TIMEZONE)

        end_text = payload.get("endDate")
        end_iso = None
        if end_text:
            try:
                end_dt = parse(end_text)
            except Exception:
                end_dt = None
            if end_dt is not None:
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=TIMEZONE)
                end_iso = end_dt.isoformat()

        description = payload.get("description", "")
        image_url = payload.get("image", "")
        if isinstance(image_url, list):
            image_url = image_url[0] if image_url else ""

        event = {
            "name": unescape(payload.get("name", "")),
            "description": unescape(description),
            "startDate": start_dt.isoformat(),
            "url": event_url,
            "status": "ACTIVE",
            "location": dict(DEFAULT_LOCATION),
            "imageUrl": image_url,
            "recurring": False,
            "scrapeTime": scraped_at,
        }
        if end_iso:
            event["endTime"] = end_iso

        events.append(event)

    return events


if __name__ == "__main__":
    import json as _json

    print(_json.dumps(scrape_events(), indent=2))
