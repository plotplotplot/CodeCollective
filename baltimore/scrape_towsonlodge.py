from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

CALENDAR_API = (
    "https://calendar.apps.secureserver.net/v1/events"
    "/c4d0c2bd-68d3-4b83-b16e-0cc2806d19f7"
    "/c485877c-aa52-4565-9eff-377b3ca7a1b9"
    "/f9967dcf-621d-4a04-9803-3735b1bd3fdf"
)
SOURCE_URL = "https://towsonlodge.us/calendar-%26-events"
TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_LOCATION = {
    "name": "Towson Lodge #79",
    "address": "505 York Rd",
    "city": "Towson",
    "state": "MD",
    "postalCode": "21204",
    "country": "US",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://towsonlodge.us/",
    "Origin": "https://towsonlodge.us",
}


def scrape_events() -> list[dict]:
    scraped_at = datetime.now(TIMEZONE).isoformat()

    resp = requests.get(CALENDAR_API, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    payload = resp.json()

    raw_events: list[dict]
    if isinstance(payload, list):
        raw_events = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        candidate = (
            payload.get("events")
            or payload.get("items")
            or payload.get("data")
            or []
        )
        if isinstance(candidate, list):
            raw_events = [item for item in candidate if isinstance(item, dict)]
        else:
            raw_events = []
    else:
        raw_events = []

    return [_normalize(e, scraped_at) for e in raw_events]


def _normalize(event: dict, scraped_at: str) -> dict:
    start_raw = event.get("startDate") or event.get("start") or ""
    try:
        dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TIMEZONE)
        start_iso = dt.isoformat()
    except Exception:
        start_iso = start_raw

    loc = event.get("location")
    location = DEFAULT_LOCATION.copy()
    if isinstance(loc, dict):
        location.update({k: v for k, v in loc.items() if v})
    elif isinstance(loc, str) and loc.strip():
        location["name"] = loc.strip()

    return {
        "name": event.get("title") or event.get("name", ""),
        "description": event.get("description") or event.get("summary") or "",
        "startDate": start_iso,
        "url": SOURCE_URL,
        "status": "ACTIVE",
        "location": location,
        "imageUrl": event.get("imageUrl") or "",
        "recurring": event.get("recurring", False),
        "scrapeTime": scraped_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Towson Lodge events.")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    try:
        events = scrape_events()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.debug:
        print(f"Fetched {len(events)} events from {CALENDAR_API}", flush=True)

    print(json.dumps(events, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
