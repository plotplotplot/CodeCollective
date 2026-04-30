from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from dateutil.parser import parse
from zoneinfo import ZoneInfo


SOURCE_URL = "https://redemmas.org/events/"
BASE_URL = "https://redemmas.org"
TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
HEADERS = {"User-Agent": "Mozilla/5.0"}
DEFAULT_LOCATION = {
    "name": "Red Emma's",
    "address": "3128 Greenmount Ave",
    "city": "Baltimore",
    "state": "MD",
    "country": "US",
}
DATE_PATTERN = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+[A-Za-z]+\s+\d{1,2}(st|nd|rd|th)?\s+\d{4}",
    re.IGNORECASE,
)
TIME_PATTERN = re.compile(r"\b\d{1,2}:\d{2}\s*(am|pm)\b", re.IGNORECASE)


def _clean_text(value: str) -> str:
    return " ".join((value or "").replace("\xa0", " ").split()).strip()


def _extract_start_iso(date_text: str, time_text: str) -> Optional[str]:
    if not date_text:
        return None

    date_clean = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", _clean_text(date_text), flags=re.IGNORECASE)
    time_clean = _clean_text(time_text)

    parsed_dt = parse(f"{date_clean} {time_clean}".strip(), fuzzy=True)
    if parsed_dt.tzinfo is None:
        parsed_dt = parsed_dt.replace(tzinfo=TIMEZONE)

    return parsed_dt.isoformat()


def _find_event_container(title_anchor: Tag, href: str) -> Optional[Tag]:
    for parent in title_anchor.parents:
        if not isinstance(parent, Tag) or parent.name != "div":
            continue
        if not parent.select_one(f'a[href="{href}"] > h2'):
            continue
        if len(parent.select("div.font-subhed")) >= 2:
            return parent
    return None


def _extract_image_url(container: Tag) -> str:
    # Gatsby renders a placeholder SVG in `img[src]` and the real asset in
    # `data-src` / `data-srcset` on the main image node.
    candidates = []

    for selector in (
        "img[data-main-image][data-src]",
        "img[data-gatsby-image-ssr][data-src]",
        "img[data-src]",
        "source[data-srcset]",
        "img[data-main-image][src]",
        "img[src]",
    ):
        node = container.select_one(selector)
        if not node:
            continue

        if node.name == "source":
            srcset = (node.get("data-srcset") or "").strip()
            first = srcset.split(",", 1)[0].strip()
            if first:
                candidates.append(first.split(" ", 1)[0].strip())
            continue

        image_url = (node.get("data-src") or node.get("src") or "").strip()
        if image_url:
            candidates.append(image_url)

    for image_url in candidates:
        lower = image_url.lower()
        if lower.startswith("data:image/svg+xml"):
            continue
        if lower.startswith("data:"):
            continue
        return urljoin(BASE_URL, image_url)

    return ""


def parse_events_html(html: str, source_url: str = SOURCE_URL) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    scraped_at = datetime.now(TIMEZONE).isoformat()
    events: List[Dict] = []
    seen_urls = set()

    for title_anchor in soup.select('a[href^="/events/"]:has(> h2)'):
        href = (title_anchor.get("href") or "").strip()
        if not href:
            continue

        event_url = urljoin(source_url, href)
        if event_url in seen_urls:
            continue

        title_node = title_anchor.select_one("h2")
        if not title_node:
            continue

        container = _find_event_container(title_anchor, href)
        if not container:
            continue

        subheads = [_clean_text(node.get_text(" ", strip=True)) for node in container.select("div.font-subhed")]
        date_text = next((text for text in subheads if DATE_PATTERN.search(text)), "")
        time_text = next((text for text in subheads if TIME_PATTERN.search(text)), "")
        location_text = next(
            (
                text
                for text in subheads
                if text
                and text != date_text
                and text != time_text
                and not DATE_PATTERN.search(text)
                and not TIME_PATTERN.search(text)
            ),
            "",
        )

        start_iso = _extract_start_iso(date_text, time_text)
        if not start_iso:
            continue

        description_node = container.select_one("div.font-text.pt-3")
        description = _clean_text(description_node.get_text(" ", strip=True)) if description_node else ""

        location = dict(DEFAULT_LOCATION)
        if location_text:
            location["name"] = location_text

        events.append(
            {
                "name": unescape(_clean_text(title_node.get_text(" ", strip=True))),
                "description": unescape(description),
                "startDate": start_iso,
                "url": event_url,
                "status": "ACTIVE",
                "location": location,
                "imageUrl": _extract_image_url(container),
                "recurring": False,
                "scrapeTime": scraped_at,
            }
        )
        seen_urls.add(event_url)

    return events


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return parse_events_html(response.text, source_url=url)


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
