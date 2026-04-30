import re
from datetime import datetime, time, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


EVENTS_URL = "https://transformpikesvillearmory.org/events"
BASE_URL = "https://transformpikesvillearmory.org"
TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
DEFAULT_START_TIME = time(12, 0)
DEFAULT_DURATION = timedelta(hours=1)
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
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
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return " ".join(text.replace("\xa0", " ").split())


def parse_year(soup):
    modified_tag = soup.find("meta", attrs={"property": "article:modified_time"})
    if modified_tag and modified_tag.get("content"):
        try:
            return datetime.fromisoformat(modified_tag["content"]).year
        except ValueError:
            pass
    return datetime.now(TIMEZONE).year


def parse_date_label(label, year):
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", clean_text(label), flags=re.IGNORECASE)

    range_match = re.match(
        r"([A-Za-z]+)\s+(\d{1,2})\s*-\s*([A-Za-z]+)\s+(\d{1,2})$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if range_match:
        start_month = MONTHS[range_match.group(1).lower()]
        start_day = int(range_match.group(2))
        end_month = MONTHS[range_match.group(3).lower()]
        end_day = int(range_match.group(4))
        return (
            datetime(year, start_month, start_day, tzinfo=TIMEZONE),
            datetime(year, end_month, end_day, tzinfo=TIMEZONE),
        )

    series_match = re.match(r"([A-Za-z]+)\s+(.+)$", cleaned)
    if series_match:
        month = MONTHS.get(series_match.group(1).lower())
        day_values = [int(day) for day in re.findall(r"\d{1,2}", series_match.group(2))]
        if month and day_values:
            return (
                datetime(year, month, min(day_values), tzinfo=TIMEZONE),
                datetime(year, month, max(day_values), tzinfo=TIMEZONE),
            )

    return None, None


def parse_time_range(text):
    cleaned = clean_text(text)

    explicit_match = re.search(
        r"from\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)?\s+to\s+(\d{1,2}(?::\d{2})?)\s*(am|pm)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if explicit_match:
        start_time = parse_clock(explicit_match.group(1), explicit_match.group(2) or explicit_match.group(4))
        end_time = parse_clock(explicit_match.group(3), explicit_match.group(4))
        return start_time, end_time

    compact_match = re.search(
        r"(\d{1,2})(?::(\d{2}))?\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if compact_match:
        start_time = parse_clock(
            f"{compact_match.group(1)}:{compact_match.group(2) or '00'}",
            compact_match.group(5),
        )
        end_time = parse_clock(
            f"{compact_match.group(3)}:{compact_match.group(4) or '00'}",
            compact_match.group(5),
        )
        if end_time <= start_time:
            # Noon/afternoon ranges like 11-1pm are rare here, but keep them sane.
            start_hour = start_time.hour
            if start_hour < 12:
                start_time = time(start_hour, start_time.minute)
        return start_time, end_time

    return DEFAULT_START_TIME, (datetime.combine(datetime.today(), DEFAULT_START_TIME) + DEFAULT_DURATION).time()


def parse_clock(clock_value, meridiem):
    normalized = clock_value.strip()
    if ":" in normalized:
        parsed = datetime.strptime(f"{normalized} {meridiem.upper()}", "%I:%M %p")
    else:
        parsed = datetime.strptime(f"{normalized} {meridiem.upper()}", "%I %p")
    return parsed.time()


def build_event(name, description, url, start_date, end_date, text):
    start_time, end_time = parse_time_range(text)
    start_dt = datetime.combine(start_date.date(), start_time, tzinfo=TIMEZONE)
    end_dt = datetime.combine(end_date.date(), end_time, tzinfo=TIMEZONE)
    if end_dt < start_dt:
        end_dt = start_dt + DEFAULT_DURATION

    return {
        "name": name,
        "startDate": start_dt.isoformat(),
        "endDate": end_dt.isoformat(),
        "endTime": end_dt.isoformat(),
        "description": description,
        "url": url,
        "status": "ACTIVE",
        "location": {
            "name": "Pikesville Armory",
            "address": "610 Reisterstown Road, Pikesville, MD 21208",
            "city": "Pikesville",
            "state": "MD",
            "country": "US",
        },
        "imageUrl": "",
        "recurring": False,
    }


def extract_name(paragraph, date_label, text):
    strong_texts = [clean_text(strong.get_text(" ", strip=True)) for strong in paragraph.find_all("strong")]
    for candidate in strong_texts:
        cleaned_candidate = candidate.strip()
        if ":" in cleaned_candidate:
            left, right = cleaned_candidate.split(":", 1)
            if clean_text(left).lower() == clean_text(date_label).lower() and right.strip():
                cleaned_candidate = right.strip()
        cleaned_candidate = cleaned_candidate.strip(" ,*")
        if not cleaned_candidate:
            continue
        if clean_text(date_label).lower() == cleaned_candidate.lower():
            continue
        if re.fullmatch(r"[A-Za-z]+\s+[\d,\sand]+", cleaned_candidate, flags=re.IGNORECASE):
            continue
        return cleaned_candidate

    prefix = f"{date_label} :"
    remainder = text
    if remainder.startswith(prefix):
        remainder = remainder[len(prefix):].strip()
    elif remainder.startswith(f"{date_label}:"):
        remainder = remainder[len(date_label) + 1 :].strip()

    first_sentence = remainder.split(". ", 1)[0].strip()
    return first_sentence.rstrip(".")


def extract_description(name, text):
    remainder = text
    if ":" in remainder:
        remainder = remainder.split(":", 1)[1].strip()
    if remainder.startswith(name):
        remainder = remainder[len(name) :].lstrip(" .")
    remainder = re.sub(r"\bMore info(?: and RSVP)?\s+HERE\b.*$", "", remainder, flags=re.IGNORECASE)
    remainder = re.sub(r"\bDetails coming soon\b\.?", "", remainder, flags=re.IGNORECASE)
    return remainder.strip(" .")


def scrape_events():
    try:
        response = requests.get(EVENTS_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Transform Pikesville Armory events fetch error: {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    year = parse_year(soup)
    events = []
    seen = set()

    for paragraph in soup.find_all("p"):
        text = clean_text(str(paragraph))
        if not text:
            continue
        if "Details Coming Soon:" in text or "We have the best Sponsors!" in text:
            continue

        date_match = re.match(r"^([A-Za-z]+\s+[^:]+):\s*(.+)$", text)
        if not date_match:
            continue

        date_label = date_match.group(1).strip()
        start_date, end_date = parse_date_label(date_label, year)
        if not start_date:
            continue

        links = [urljoin(BASE_URL, link.get("href")) for link in paragraph.find_all("a", href=True)]
        name = extract_name(paragraph, date_label, text)
        description = extract_description(name, text)
        event_url = links[0] if links else EVENTS_URL
        event = build_event(name, description, event_url, start_date, end_date, text)

        if "Every Tuesday" in text:
            event["recurring"] = True

        dedupe_key = f"{event['name']}::{event['startDate']}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        events.append(event)

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
