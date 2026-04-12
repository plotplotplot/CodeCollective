import re
from datetime import datetime, time, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


EVENTS_URL = "https://www.mdchamber.org/events/"
BASE_URL = "https://www.mdchamber.org"
TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
DEFAULT_START_HOUR = 9
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}


def clean_text(value):
    if not value:
        return ""
    text = value.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_event_date_label(label):
    if not label:
        return None

    first_part = clean_text(re.split(r"[∙|]", label)[0])
    date_formats = [
        ("%b %d, %Y", False),
        ("%B %d, %Y", False),
        ("%b %Y", True),
        ("%B %Y", True),
    ]

    for fmt, is_month_only in date_formats:
        try:
            parsed = datetime.strptime(first_part, fmt)
            if is_month_only:
                return datetime(parsed.year, parsed.month, 1, DEFAULT_START_HOUR, 0, tzinfo=TIMEZONE)
            return datetime(parsed.year, parsed.month, parsed.day, DEFAULT_START_HOUR, 0, tzinfo=TIMEZONE)
        except ValueError:
            continue

    return None


def parse_date_time_line(line):
    if not line:
        return None, None

    clean_line = clean_text(line)
    date_part = clean_text(clean_line.split("|")[0])
    date_obj = None
    for fmt in ("%A, %B %d, %Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            date_obj = datetime.strptime(date_part, fmt).date()
            break
        except ValueError:
            continue

    if date_obj is None:
        return None, None

    time_match = re.search(
        r"(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)",
        clean_line,
        flags=re.IGNORECASE,
    )
    if time_match:
        start_time = datetime.strptime(time_match.group(1).upper(), "%I:%M %p").time()
        end_time = datetime.strptime(time_match.group(2).upper(), "%I:%M %p").time()
    else:
        start_time = time(DEFAULT_START_HOUR, 0)
        end_time = time(DEFAULT_START_HOUR + 1, 0)

    start_dt = datetime.combine(date_obj, start_time, tzinfo=TIMEZONE)
    end_dt = datetime.combine(date_obj, end_time, tzinfo=TIMEZONE)
    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(hours=1)

    return start_dt, end_dt


def extract_event_details(event_url):
    try:
        response = requests.get(event_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"MD Chamber detail fetch error ({event_url}): {exc}")
        return {}
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    details = {}

    og_description = soup.find("meta", attrs={"property": "og:description"})
    if og_description and og_description.get("content"):
        details["description"] = clean_text(og_description["content"])

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        details["imageUrl"] = clean_text(og_image["content"])

    details_heading = soup.find(
        lambda tag: tag.name in {"h2", "h3", "h4"}
        and "event details" in tag.get_text(" ", strip=True).lower()
    )
    if not details_heading:
        return details

    details_module = None

    cursor = details_heading
    for _ in range(10):
        cursor = cursor.find_next_sibling()
        if cursor is None:
            break
        classes = " ".join(cursor.get("class", []))
        if cursor.name == "div" and "fl-module-rich-text" in classes:
            details_module = cursor
            break

    if details_module is None:
        heading_module = details_heading.find_parent(
            "div", class_=lambda cls: cls and "fl-module-heading" in cls
        )
        if heading_module is not None:
            details_module = heading_module.find_next_sibling(
                "div", class_=lambda cls: cls and "fl-module-rich-text" in cls
            )

    if not details_module:
        return details

    paragraphs = [clean_text(p.get_text(" ", strip=True)) for p in details_module.select("p")]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        return details

    start_dt, end_dt = parse_date_time_line(paragraphs[0])
    if start_dt:
        details["startDate"] = start_dt.isoformat()
    if end_dt:
        details["endDate"] = end_dt.isoformat()
        details["endTime"] = end_dt.isoformat()

    if len(paragraphs) > 1:
        location_line = paragraphs[1]
        first_comma = location_line.find(",")
        location_name = location_line[:first_comma].strip() if first_comma > 0 else location_line
        details["location"] = {
            "name": location_name,
            "address": location_line,
            "city": "Baltimore",
            "state": "MD",
            "country": "US",
        }

    return details


def scrape_events():
    try:
        response = requests.get(EVENTS_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"MD Chamber events fetch error: {exc}")
        return []
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("div.upcoming-events")
    events = []
    seen = set()

    for row in rows:
        title_el = row.select_one("h3 .fl-heading-text")
        if not title_el:
            continue
        name = clean_text(title_el.get_text(" ", strip=True))
        if not name:
            continue

        link_el = row.select_one("h3 a[href]")
        url = urljoin(BASE_URL, link_el.get("href", "").strip()) if link_el else ""

        meta_el = row.select_one("h2 .fl-heading-text")
        meta_text = clean_text(meta_el.get_text(" ", strip=True)) if meta_el else ""

        desc_el = row.select_one(".fl-rich-text p")
        description = clean_text(desc_el.get_text(" ", strip=True)) if desc_el else ""

        start_dt = parse_event_date_label(meta_text)
        end_dt = start_dt + timedelta(hours=1) if start_dt else None

        event = {
            "name": name,
            "startDate": start_dt.isoformat() if start_dt else "",
            "endDate": end_dt.isoformat() if end_dt else "",
            "endTime": end_dt.isoformat() if end_dt else "",
            "description": description,
            "url": url or EVENTS_URL,
            "status": "ACTIVE",
            "location": {
                "name": "",
                "address": "",
                "city": "Baltimore",
                "state": "MD",
                "country": "US",
            },
            "imageUrl": "",
            "recurring": False,
        }

        if url:
            detail_data = extract_event_details(url)
            if detail_data:
                event.update(detail_data)

        dedupe_key = event["url"] or f"{event['name']}::{event.get('startDate', '')}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        events.append(event)

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
