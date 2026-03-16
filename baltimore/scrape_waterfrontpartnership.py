from __future__ import annotations

import hashlib
from datetime import datetime
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo


BASE_URL = "https://www.waterfrontpartnership.org"
EVENTS_URL = f"{BASE_URL}/events-calendar"
IMAGE_URL = "https://images.squarespace-cdn.com/content/v1/63974fbfdb846962ef990e53/9154a62f-d346-45e7-b4d0-fd6b44f79b66/WP-logo-color.png"
TIMEZONE = ZoneInfo("America/New_York")


def _parse_datetime(date_text: str, time_text: Optional[str]) -> Optional[str]:
    date_text = " ".join(date_text.split())
    if not date_text:
        return None

    date_formats = ["%A, %B %d, %Y", "%a, %b %d, %Y"]
    if time_text:
        normalized_time = (
            time_text.replace("\u202f", " ")
            .replace("\xa0", " ")
            .strip()
            .upper()
        )
        dt = None
        for date_format in date_formats:
            try:
                dt = datetime.strptime(f"{date_text} {normalized_time}", f"{date_format} %I:%M %p")
                break
            except ValueError:
                continue
    else:
        dt = None
        for date_format in date_formats:
            try:
                dt = datetime.strptime(date_text, date_format)
                break
            except ValueError:
                continue

    if dt is None:
        raise ValueError(f"Unsupported Waterfront Partnership date: {date_text} / {time_text}")

    return dt.replace(tzinfo=TIMEZONE).isoformat()


def _extract_address(li_tag) -> str:
    map_link = li_tag.find("a", class_="eventlist-meta-address-maplink")
    if map_link and map_link.get("href"):
        query = parse_qs(urlsplit(map_link["href"]).query).get("q", [])
        if query:
            return query[0]
    return " ".join(li_tag.stripped_strings)


def scrape_events() -> List[Dict[str, object]]:
    response = requests.get(EVENTS_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict[str, object]] = []

    for article in soup.select("article.eventlist-event--upcoming"):
        title_link = article.select_one("a.eventlist-title-link")
        date_tags = article.select("li.eventlist-meta-date time.event-date")
        time_tags = article.select("time.event-time-localized-start, time.event-time-localized-end, li.eventlist-meta-time time.event-time-localized")
        address_li = article.select_one("li.eventlist-meta-address")
        excerpt = article.select_one("div.eventlist-excerpt")
        thumbnail = article.select_one("a.eventlist-column-thumbnail img")

        if not title_link or not date_tags:
            continue

        name = " ".join(title_link.get_text(" ", strip=True).split())
        event_url = urljoin(BASE_URL, title_link.get("href", ""))

        start_date_text = date_tags[0].get_text(" ", strip=True)
        end_date_text = date_tags[-1].get_text(" ", strip=True)
        start_time_text = time_tags[0].get_text(" ", strip=True) if time_tags else None
        end_time_text = time_tags[-1].get_text(" ", strip=True) if len(time_tags) > 1 else None

        start_iso = _parse_datetime(start_date_text, start_time_text)
        end_iso = _parse_datetime(end_date_text, end_time_text) if end_time_text else None

        location_name = ""
        location_address = ""
        if address_li:
            address_text = _extract_address(address_li)
            location_name = next(address_li.stripped_strings, "")
            if location_name == "(map)":
                location_name = ""
            location_address = address_text.replace("(map)", "").strip()

        image_url = ""
        if thumbnail:
            image_url = thumbnail.get("data-src") or thumbnail.get("src") or ""

        events.append(
            {
                "id": hashlib.md5(event_url.encode()).hexdigest()[:16],
                "name": name,
                "startDate": start_iso,
                "endTime": end_iso,
                "description": unescape(excerpt.get_text("\n", strip=True)) if excerpt else "",
                "url": event_url,
                "status": "ACTIVE",
                "location": {
                    "name": location_name,
                    "address": location_address,
                },
                "imageUrl": image_url or IMAGE_URL,
                "recurring": False,
                "scrapeTime": scraped_at,
            }
        )

    return events
