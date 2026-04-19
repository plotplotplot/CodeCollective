from datetime import datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


EVENTS_URL = "https://www.greaterbaltimorechamber.org/calendarandevents/eventcalendar"
API_URL = "https://api.chambermate.com/core/biz/webPresence/getEventsInfo"
BASE_URL = "https://www.greaterbaltimorechamber.org"
TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
DEFAULT_DURATION = timedelta(hours=1)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE_URL,
    "Referer": EVENTS_URL,
}
QUERY = {
    "websiteShorthand": "greaterbaltimorechamber",
    "websiteDomain": "www.greaterbaltimorechamber.org",
    "isPortal": False,
    "includeCategories": True,
    "includePastEvents": False,
    "rowCount": 500,
}


def parse_local_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TIMEZONE)
    return parsed


def build_location(address):
    address = address or {}
    street_parts = [address.get("street1"), address.get("street2")]
    street_parts = [part.strip() for part in street_parts if isinstance(part, str) and part.strip()]

    city = (address.get("city") or "").strip()
    state = (address.get("stateCode") or "").strip()
    postal = (address.get("zip") or "").strip()
    country = (address.get("countryCode") or "US").strip()

    locality = ", ".join(part for part in [city, state] if part)
    address_parts = []
    if street_parts:
        address_parts.append(" ".join(street_parts))
    if locality:
        address_parts.append(locality)
    if postal:
        address_parts.append(postal)

    return {
        "name": (address.get("name") or "").strip(),
        "address": ", ".join(address_parts),
        "city": city,
        "state": state,
        "country": "US" if country == "USA" else country,
    }


def normalize_event_url(event):
    for candidate in (
        event.get("eventDetailUrl"),
        event.get("eventUrl"),
        event.get("learnMoreURL"),
    ):
        if not candidate:
            continue
        candidate = candidate.strip()
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return candidate
        if candidate.startswith("greaterbaltimorechamber.org/"):
            return f"https://www.{candidate}"
        return urljoin(f"{BASE_URL}/", candidate)
    return EVENTS_URL


def normalize_image_url(event):
    account_logo = event.get("accountLogoInfo") or {}
    if isinstance(account_logo, dict):
        for key in ("url", "publicUrl", "downloadUrl"):
            value = account_logo.get(key)
            if value:
                return value
    return ""


def clean_description(value):
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return " ".join(text.split())


def scrape_events():
    try:
        response = requests.get(
            API_URL,
            params=QUERY,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Greater Baltimore Chamber events fetch error: {exc}")
        return []

    payload = response.json().get("data", {})
    events = []
    seen = set()

    for raw_event in payload.get("events", []):
        start_dt = parse_local_datetime(raw_event.get("startDateTime"))
        end_dt = parse_local_datetime(raw_event.get("endDateTime"))

        if not start_dt:
            continue
        if end_dt is None or end_dt < start_dt:
            end_dt = start_dt + DEFAULT_DURATION

        event_url = normalize_event_url(raw_event)
        dedupe_key = raw_event.get("activityKey") or f"{raw_event.get('eventName', '')}::{start_dt.isoformat()}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        events.append(
            {
                "name": (raw_event.get("eventName") or "").strip(),
                "startDate": start_dt.isoformat(),
                "endDate": end_dt.isoformat(),
                "endTime": end_dt.isoformat(),
                "description": clean_description(
                    raw_event.get("eventFullDescription") or raw_event.get("eventDescription") or ""
                ),
                "url": event_url,
                "status": "ACTIVE",
                "location": build_location(raw_event.get("address")),
                "imageUrl": normalize_image_url(raw_event),
                "eventType": raw_event.get("eventTypeCode", ""),
                "recurring": False,
            }
        )

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
