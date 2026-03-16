#!/usr/bin/env python3
"""
Scrape upcoming events from https://usgpo.github.io/innovation/events/.

Uses only the Python standard library plus `requests` (already available in
this environment). The scraper:
1. Loads the events index page and finds the "Upcoming Events" list.
2. Follows each event link.
3. Extracts description, date/time, location, and meeting/registration link.
4. Emits a JSON array shaped like the sample payload provided.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import urllib.parse
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

import requests


BASE_URL = "https://usgpo.github.io/innovation"
INDEX_URL = f"{BASE_URL}/events/"
DEFAULT_TZ_OFFSET = "-05:00"  # Eastern Time; adjust if the site adds explicit offsets


def fetch_text(url: str) -> str:
    """Fetch a URL and return its decoded text."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def html_to_text(fragment: str) -> str:
    """
    Convert a small HTML fragment into readable text while preserving simple line breaks.
    """
    if not fragment:
        return ""

    # Normalize common break tags into new lines.
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?i)</p>|</div>|</li>", "\n", fragment)
    # Strip remaining markup.
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = html.unescape(fragment)
    lines = [line.strip() for line in fragment.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


class EventsIndexParser(HTMLParser):
    """HTML parser tuned to the structure of the events index page."""

    def __init__(self) -> None:
        super().__init__()
        self.current_h2: List[str] = []
        self.section: Optional[str] = None
        self.in_h2 = False
        self.in_li = False
        self.in_anchor = False
        self.in_em = False
        self.current_item: Dict[str, str] = {}
        self.events: List[Dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "h2":
            # New section header; stop capturing upcoming items until we confirm the header text.
            self.in_h2 = True
            self.current_h2 = []
            return

        if self.section == "upcoming":
            if tag == "li":
                self.in_li = True
                self.current_item = {"name": "", "url": "", "date": ""}
            elif tag == "a" and self.in_li:
                self.in_anchor = True
                href = dict(attrs).get("href", "") if attrs else ""
                self.current_item["url"] = href
            elif tag == "em" and self.in_li:
                self.in_em = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            header = " ".join(self.current_h2).strip().lower()
            if header.startswith("upcoming events"):
                self.section = "upcoming"
            elif self.section == "upcoming":
                # The header after "Upcoming Events" ends the section.
                self.section = None
            self.in_h2 = False
            self.current_h2 = []
            return

        if self.section == "upcoming":
            if tag == "li" and self.in_li:
                self.events.append(self.current_item)
                self.in_li = False
            elif tag == "a":
                self.in_anchor = False
            elif tag == "em":
                self.in_em = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self.in_h2:
            self.current_h2.append(text)
        elif self.section == "upcoming" and self.in_li:
            if self.in_anchor:
                self.current_item["name"] += text
            elif self.in_em:
                self.current_item["date"] += text


def parse_index_upcoming(html_content: str) -> List[Dict[str, str]]:
    """Return the list of upcoming event records (name, url, date) from the index."""
    parser = EventsIndexParser()
    parser.feed(html_content)
    return parser.events


def extract_section(html_content: str, section_id: str) -> str:
    """
    Grab the fragment that follows an <h3 id="{section_id}"> ... </h3> block
    up to the next <h3> or container end.
    """
    pattern = rf'<h3[^>]*id="{section_id}"[^>]*>.*?</h3>(.*?)(?=<h3[^>]*id="|</div>)'
    match = re.search(pattern, html_content, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def extract_first_link(html_content: str) -> Optional[str]:
    """Return the first href in a fragment, if any."""
    match = re.search(r'href="([^"]+)"', html_content)
    return match.group(1) if match else None


def extract_first_image(html_content: str) -> Optional[str]:
    """Return the first image URL in a fragment, if any."""
    match = re.search(r'<img[^>]+src="([^"]+)"', html_content, flags=re.IGNORECASE)
    return match.group(1) if match else None


def to_24h(time_str: str, ampm: str) -> str:
    hour, minute = map(int, time_str.split(":"))
    ampm_upper = ampm.upper()
    if ampm_upper == "PM" and hour != 12:
        hour += 12
    if ampm_upper == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def parse_datetime_block(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract start and end datetimes (ISO 8601 with offset) from a block of text.
    Falls back to date-only when times are absent.
    """
    normalized = text.replace("\u2013", "-").replace("\u2014", "-")
    date_match = re.search(r"([A-Za-z]+ \d{1,2}, \d{4})", normalized)
    event_date = None
    if date_match:
        try:
            event_date = dt.datetime.strptime(date_match.group(1), "%B %d, %Y").date()
        except ValueError:
            event_date = None

    times = re.findall(r"(\d{1,2}:\d{2})\s*(AM|PM)", normalized, flags=re.IGNORECASE)

    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    if event_date and times:
        start_iso = f"{event_date}T{to_24h(times[0][0], times[0][1])}:00{DEFAULT_TZ_OFFSET}"
        if len(times) > 1:
            end_iso = f"{event_date}T{to_24h(times[1][0], times[1][1])}:00{DEFAULT_TZ_OFFSET}"
    elif event_date:
        start_iso = f"{event_date}T00:00:00{DEFAULT_TZ_OFFSET}"

    return start_iso, end_iso


def parse_event_detail(event_url: str) -> Dict[str, Optional[str]]:
    """Fetch and parse a single event page."""
    html_content = fetch_text(event_url)
    description_block = extract_section(html_content, "description")
    date_block = extract_section(html_content, "date-and-time")
    location_block = extract_section(html_content, "location")
    meeting_block = extract_section(html_content, "meeting")

    description = html_to_text(description_block)
    date_text = html_to_text(date_block)
    location_text = html_to_text(location_block)
    registration_url = extract_first_link(meeting_block) or event_url
    image_url = None
    for block in (description_block, meeting_block, location_block):
        image_url = extract_first_image(block or "")
        if image_url:
            break
    start_iso, end_iso = parse_datetime_block(date_text)

    location_name = location_text.split("\n")[0] if location_text else ""

    return {
        "description": description,
        "startDate": start_iso,
        "endTime": end_iso,
        "url": urllib.parse.urljoin(event_url, registration_url),
        "location_name": location_name,
        "imageUrl": urllib.parse.urljoin(event_url, image_url) if image_url else None,
        "source": event_url,
    }


def scrape_upcoming_events() -> List[Dict[str, object]]:
    """Orchestrate the scraping of all upcoming events."""
    index_html = fetch_text(INDEX_URL)
    upcoming = parse_index_upcoming(index_html)
    scraped_at = dt.datetime.now().isoformat(sep=" ", timespec="microseconds")

    results: List[Dict[str, object]] = []
    for item in upcoming:
        detail_url = urllib.parse.urljoin(BASE_URL, item["url"])
        slug = urllib.parse.urlparse(detail_url).path.rstrip("/").split("/")[-1]
        details = parse_event_detail(detail_url)

        results.append(
            {
                "id": slug,
                "name": item["name"],
                "description": details["description"],
                "startDate": details["startDate"],
                "endTime": details["endTime"],
                "url": details["url"],
                "status": "ACTIVE",
                "source": details["source"],
                "location": {
                    "name": details["location_name"],
                    "address": "",
                    "city": "",
                    "state": "",
                    "country": "",
                },
                "imageUrl": details["imageUrl"],
                "scrapeTime": scraped_at,
            }
        )

    return results


def main() -> None:
    events = scrape_upcoming_events()
    json.dump(events, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
