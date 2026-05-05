from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from icalendar import Calendar
import pytz
from dateutil.parser import parse as parse_date

from http_client import build_session, polite_get


TIMEZONE = pytz.timezone("America/New_York")
LOOKAHEAD_DAYS = 365


def _normalize_datetime(value, default_tz=TIMEZONE):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return default_tz.localize(value)
        return value.astimezone(default_tz)
    # date object
    return default_tz.localize(datetime.combine(value, datetime.min.time()))


def _parse_ics_event(ics_bytes: bytes, fallback_url: str) -> Dict | None:
    cal = Calendar.from_ical(ics_bytes)
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        summary = str(component.get("summary", "")).strip()
        dtstart_prop = component.get("dtstart")
        if not summary or not dtstart_prop:
            return None

        dtstart = _normalize_datetime(dtstart_prop.dt)
        dtend_prop = component.get("dtend")
        dtend = _normalize_datetime(dtend_prop.dt) if dtend_prop else dtstart
        location = str(component.get("location", "")).strip()
        description = str(component.get("description", "")).strip()
        event_url = str(component.get("url", "")).strip() or fallback_url

        return {
            "name": summary,
            "description": description,
            "startDate": dtstart.isoformat(),
            "endTime": dtend.isoformat(),
            "url": event_url,
            "status": "ACTIVE",
            "location": {"name": location, "address": location},
            "imageUrl": "",
            "source": fallback_url,
        }
    return None


def scrape(source_url: str) -> List[Dict]:
    session = build_session(user_agent="CodeCollectiveBot/1.0")
    response = polite_get(session, source_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    seen = set()
    for anchor in soup.select('a[href*="View.ashx?M=IC"]'):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue
        full_url = urljoin(source_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        links.append(full_url)

    now = datetime.now(TIMEZONE)
    future_cutoff = now + timedelta(days=LOOKAHEAD_DAYS)
    events: List[Dict] = []
    seen_event_keys = set()

    for ics_url in links:
        try:
            ics_resp = polite_get(
                session,
                ics_url,
                timeout=30,
                headers={"Accept": "text/calendar, text/plain, */*"},
            )
            ics_resp.raise_for_status()
            event = _parse_ics_event(ics_resp.content, source_url)
            if not event:
                continue
            start_dt = datetime.fromisoformat(event["startDate"])
            if start_dt < now or start_dt > future_cutoff:
                continue
            key = (event["name"].strip().lower(), event["startDate"])
            if key in seen_event_keys:
                continue
            seen_event_keys.add(key)
            events.append(event)
        except Exception:
            continue

    # Fallback path for Legistar pages that expose meetings only in grid rows.
    if not events:
        grid = soup.find("table", id=lambda value: isinstance(value, str) and "gridCalendar" in value)
        if grid:
            rows = grid.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 5:
                    continue
                name = " ".join(cells[0].get_text(" ", strip=True).split())
                date_text = " ".join(cells[1].get_text(" ", strip=True).split())
                time_text = " ".join(cells[3].get_text(" ", strip=True).split())
                location = " ".join(cells[4].get_text(" ", strip=True).split())
                if not name or not date_text or "No records were found" in name:
                    continue
                try:
                    start_dt = parse_date(f"{date_text} {time_text}".strip(), fuzzy=True)
                    if start_dt.tzinfo is None:
                        start_dt = TIMEZONE.localize(start_dt)
                    else:
                        start_dt = start_dt.astimezone(TIMEZONE)
                except Exception:
                    continue
                if start_dt < now or start_dt > future_cutoff:
                    continue
                key = (name.strip().lower(), start_dt.isoformat())
                if key in seen_event_keys:
                    continue
                seen_event_keys.add(key)
                detail_url = source_url
                first_link = row.find("a", href=True)
                if first_link:
                    detail_url = urljoin(source_url, first_link["href"])
                events.append(
                    {
                        "name": name,
                        "description": "",
                        "startDate": start_dt.isoformat(),
                        "endTime": "",
                        "url": detail_url,
                        "status": "ACTIVE",
                        "location": {"name": location, "address": location},
                        "imageUrl": "",
                        "source": source_url,
                    }
                )

    return events
