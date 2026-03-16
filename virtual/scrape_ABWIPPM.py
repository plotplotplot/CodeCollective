#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from hashlib import md5

import requests


EVENTS_URL = "https://www.abwippm.org/events"
EVENT_DETAIL_BASE = "https://www.abwippm.org/events-1/"
USER_AGENT = "Mozilla/5.0"
TIMEOUT = 30


def fetch_events_page():
    response = requests.get(
        EVENTS_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def extract_wix_events_payload(html):
    # The Wix page embeds the event list in a large JSON blob inside the viewer model.
    marker = '"events":{"events":['
    marker_index = html.find(marker)
    if marker_index == -1:
        raise ValueError("Could not find embedded Wix events payload")

    payload, _ = json.JSONDecoder().raw_decode(html[marker_index - 1 :])
    return payload


def normalize_location(raw_location):
    raw_location = raw_location or {}
    if isinstance(raw_location, str):
        return {
            "name": raw_location,
            "address": "",
            "city": "",
            "state": "",
            "country": "",
        }

    if not isinstance(raw_location, dict):
        return {
            "name": "",
            "address": "",
            "city": "",
            "state": "",
            "country": "",
        }

    address = raw_location.get("address") or {}
    if isinstance(address, str):
        address_text = address
        address = {}
    else:
        address_text = address.get("formatted", "") or address.get("addressLine", "")

    return {
        "name": raw_location.get("name", ""),
        "address": address_text,
        "city": address.get("city", ""),
        "state": address.get("subdivision", ""),
        "country": address.get("countryFullname", "") or address.get("country", ""),
    }


def build_event_url(event):
    slug = event.get("slug", "").strip("/")
    if slug:
        return f"{EVENT_DETAIL_BASE}{slug}"
    return EVENTS_URL


def build_event_id(event):
    if event.get("id"):
        return event["id"]
    digest = md5(
        f"{event.get('title', '')}|{event.get('slug', '')}|{event.get('publishedDate', '')}".encode(
            "utf-8"
        )
    ).hexdigest()
    return digest


def normalize_event(event, date_lookup):
    scheduling = event.get("scheduling", {})
    config = scheduling.get("config", {})
    event_dates = date_lookup.get(event.get("id"), {})
    start_date = event_dates.get("startDateISOFormatNotUTC") or config.get("startDate")
    end_date = event_dates.get("endDateISOFormatNotUTC") or config.get("endDate")
    description = (event.get("description") or event.get("about") or "").strip()
    status = "ACTIVE"
    if event.get("status") not in (0, None):
        status = "INACTIVE"

    return {
        "id": build_event_id(event),
        "name": event.get("title", "").strip(),
        "description": description,
        "startDate": start_date.replace("Z", "+00:00") if start_date else "",
        "endTime": end_date.replace("Z", "+00:00") if end_date else "",
        "url": build_event_url(event),
        "status": status,
        "location": normalize_location(event.get("location")),
        "imageUrl": (event.get("mainImage") or {}).get("url", ""),
        "recurring": bool(
            (
                config.get("recurrences", {}) or {}
            ).get("status")
        ),
        "scrapeTime": event.get("modified")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }


def scrape_events():
    html = fetch_events_page()
    payload = extract_wix_events_payload(html)
    wix_events = payload["events"]["events"]
    date_lookup = payload.get("dates", {}).get("events", {})
    normalized_events = [normalize_event(event, date_lookup) for event in wix_events]
    normalized_events.sort(key=lambda event: event.get("startDate", ""))
    return normalized_events


def main():
    events = scrape_events()
    print(json.dumps(events, indent=2))


if __name__ == "__main__":
    main()
