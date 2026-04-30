from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from zoneinfo import ZoneInfo


SOURCE_URL = "https://baltimore.org/events/"
BASE_URL = "https://baltimore.org"
TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
DEFAULT_EVENT_DURATION = timedelta(hours=2)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CodeCollective/1.0)",
}

GOOGLE_INFO_PATTERN = re.compile(
    r"var\s+google_info\s*=\s*(\{.*?\})\s*jQuery\(document\)\.ready",
    re.DOTALL,
)
HUMAN_DATETIME_PATTERN = re.compile(
    r"\b([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s*\|\s*"
    r"(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)"
    r"(?:\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?))?",
    re.IGNORECASE,
)


def _clean_text(value: str) -> str:
    return " ".join(unescape(value or "").replace("\xa0", " ").split()).strip()


def _to_absolute_event_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(BASE_URL, href)


def _extract_event_links(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    seen = set()

    # Primary listing cards on /events/.
    for anchor in soup.select('a.this-weekend__event-container[href*="/event/"]'):
        url = _to_absolute_event_url(anchor.get("href", ""))
        if not url or url in seen:
            continue
        seen.add(url)
        links.append(url)

    # Fallback for additional event cards rendered with a different class.
    for anchor in soup.select('a.event-tease[href*="/event/"], a[href*="/event/"]'):
        url = _to_absolute_event_url(anchor.get("href", ""))
        if not url or url in seen:
            continue
        parsed = urlparse(url)
        if "/event/" not in parsed.path:
            continue
        seen.add(url)
        links.append(url)

    return links


def _parse_js_object_block(html: str) -> Optional[Dict]:
    match = GOOGLE_INFO_PATTERN.search(html)
    if not match:
        return None

    raw = match.group(1).strip()
    # Guard against occasional trailing commas in JS objects.
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def _parse_status(event_status: str) -> str:
    status = (event_status or "").lower()
    if "cancelled" in status or "canceled" in status:
        return "CANCELLED"
    if "postponed" in status:
        return "POSTPONED"
    return "ACTIVE"


def _clean_meridiem_time(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).replace(".", "").upper()


def _parse_human_datetime(date_part: str, time_part: str) -> Optional[datetime]:
    if not date_part or not time_part:
        return None

    cleaned_time = _clean_meridiem_time(time_part)
    candidate = f"{date_part.strip()} {cleaned_time}"
    for fmt in (
        "%B %d, %Y %I:%M %p",
        "%b %d, %Y %I:%M %p",
        "%B %d, %Y %I %p",
        "%b %d, %Y %I %p",
    ):
        try:
            dt = datetime.strptime(candidate, fmt)
            return dt.replace(tzinfo=TIMEZONE)
        except ValueError:
            continue
    return None


def _extract_human_datetime_range(html: str) -> tuple[Optional[datetime], Optional[datetime]]:
    text = _clean_text(BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True))
    if not text:
        return None, None

    match = HUMAN_DATETIME_PATTERN.search(text)
    if not match:
        return None, None

    date_part, start_time, end_time = match.groups()
    start_dt = _parse_human_datetime(date_part, start_time)
    if not start_dt:
        return None, None

    end_dt = _parse_human_datetime(date_part, end_time) if end_time else None
    if end_dt and end_dt < start_dt:
        end_dt = end_dt + timedelta(days=1)
    return start_dt, end_dt


def _string_has_explicit_time(value: str) -> bool:
    return bool(re.search(r"\d{1,2}:\d{2}\s*([ap]\.?m\.?)?", str(value or ""), re.IGNORECASE))


def _parse_dates(start_value: str, end_value: str) -> tuple[Optional[str], Optional[str]]:
    if not start_value:
        return None, None

    try:
        start_dt = parse(start_value)
    except Exception:
        return None, None

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=TIMEZONE)
    else:
        start_dt = start_dt.astimezone(TIMEZONE)

    end_dt = None
    if end_value:
        try:
            end_dt = parse(end_value)
        except Exception:
            end_dt = None

    if end_dt is None:
        end_dt = start_dt + DEFAULT_EVENT_DURATION
    elif end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=TIMEZONE)
    else:
        end_dt = end_dt.astimezone(TIMEZONE)

    if end_dt < start_dt:
        end_dt = start_dt + DEFAULT_EVENT_DURATION

    return start_dt.isoformat(), end_dt.isoformat()


def _normalize_location(payload: Dict) -> Dict:
    location = payload.get("location") if isinstance(payload.get("location"), dict) else {}
    address = location.get("address") if isinstance(location.get("address"), dict) else {}

    street = _clean_text(address.get("streetAddress", ""))
    city = _clean_text(address.get("addressLocality", ""))
    state = _clean_text(address.get("addressRegion", ""))
    postal = _clean_text(address.get("postalCode", ""))
    country = _clean_text(address.get("addressCountry", ""))

    address_parts = [part for part in [street, city, state, postal] if part]
    full_address = ", ".join(address_parts)

    return {
        "name": _clean_text(location.get("name", "")),
        "address": full_address,
        "city": city,
        "state": state,
        "country": country or "US",
    }


def _normalize_image(payload: Dict) -> str:
    image = payload.get("image")
    if isinstance(image, list) and image:
        return _clean_text(str(image[0]))
    if isinstance(image, str):
        return _clean_text(image)
    return ""


def _parse_event_detail(event_url: str, session: requests.Session, scrape_time: str) -> Optional[Dict]:
    try:
        response = session.get(event_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"baltimore.org event detail fetch error ({event_url}): {exc}")
        return None

    info = _parse_js_object_block(response.text)
    if not info:
        return None

    start_value = info.get("startDate", "")
    end_value = info.get("endDate", "")
    start_iso, end_iso = _parse_dates(start_value, end_value)
    if not start_iso:
        return None

    extracted_start_dt, extracted_end_dt = _extract_human_datetime_range(response.text)
    has_explicit_start_time = _string_has_explicit_time(start_value)
    has_explicit_end_time = _string_has_explicit_time(end_value)

    if extracted_start_dt and not has_explicit_start_time:
        start_iso = extracted_start_dt.isoformat()
    if extracted_end_dt and not has_explicit_end_time:
        end_iso = extracted_end_dt.isoformat()
    elif extracted_start_dt and not has_explicit_end_time:
        end_iso = (extracted_start_dt + DEFAULT_EVENT_DURATION).isoformat()

    description = _clean_text(info.get("description", ""))
    event = {
        "name": _clean_text(info.get("name", "")),
        "description": description,
        "startDate": start_iso,
        "endDate": end_iso,
        "endTime": end_iso,
        "url": event_url,
        "status": _parse_status(info.get("eventStatus", "")),
        "location": _normalize_location(info),
        "imageUrl": _normalize_image(info),
        "recurring": False,
        "scrapeTime": scrape_time,
    }

    if not event["name"]:
        return None

    return event


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"baltimore.org events fetch error: {exc}")
        return []

    event_links = _extract_event_links(response.text)
    if not event_links:
        return []

    scrape_time = datetime.now(TIMEZONE).isoformat()
    events: List[Dict] = []
    seen_urls = set()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_parse_event_detail, link, session, scrape_time) for link in event_links]
        for future in as_completed(futures):
            event = future.result()
            if not event:
                continue
            event_url = event.get("url", "")
            if event_url in seen_urls:
                continue
            seen_urls.add(event_url)
            events.append(event)

    # Keep output stable for downstream diffs.
    events.sort(key=lambda evt: (evt.get("startDate", ""), evt.get("name", "")))
    return events


if __name__ == "__main__":
    print(json.dumps(scrape_events(), indent=2))
