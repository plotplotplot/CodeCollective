import calendar
import datetime
import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup
import pytz

from http_client import build_session, polite_get


THREAD_EVENTS_API_URL = "https://my.thread.org/api/v2/help_center/en-us/categories/360005554572/articles.json"
EASTERN_TZ = pytz.timezone("America/New_York")

WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _strip_html(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


def _extract_location(body_html: str) -> str:
    text = _strip_html(body_html)
    location_match = re.search(r"Location:\s*(.+)", text, flags=re.IGNORECASE)
    if location_match:
        return location_match.group(1).strip()
    address_match = re.search(r"(?:\d{2,6}\s+[^,\n]+,\s*Baltimore,\s*MD\s*\d{5})", text, flags=re.IGNORECASE)
    if address_match:
        return address_match.group(1).strip()
    return "TouchPoint Baltimore"


def _parse_time_range(text: str) -> tuple[datetime.time, datetime.time]:
    match = re.search(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return datetime.time(15, 0), datetime.time(18, 0)

    sh, sm, sap, eh, em, eap = match.groups()
    sh = int(sh)
    sm = int(sm or "0")
    eh = int(eh)
    em = int(em or "0")
    sap = sap.lower()
    eap = eap.lower()

    if sap == "pm" and sh != 12:
        sh += 12
    if sap == "am" and sh == 12:
        sh = 0
    if eap == "pm" and eh != 12:
        eh += 12
    if eap == "am" and eh == 12:
        eh = 0

    return datetime.time(sh, sm), datetime.time(eh, em)


def _next_weekday(base_date: datetime.date, target_weekday: int) -> datetime.date:
    days_ahead = (target_weekday - base_date.weekday()) % 7
    return base_date + datetime.timedelta(days=days_ahead)


def _nth_weekday_of_month(year: int, month: int, weekday: int, nth: int) -> datetime.date | None:
    month_cal = calendar.monthcalendar(year, month)
    candidates = [week[weekday] for week in month_cal if week[weekday] != 0]
    if 1 <= nth <= len(candidates):
        return datetime.date(year, month, candidates[nth - 1])
    return None


def _expand_schedule_dates(article_title: str, body_text: str) -> List[datetime.date]:
    lower = f"{article_title}\n{body_text}".lower()
    today = datetime.datetime.now(EASTERN_TZ).date()
    horizon = today + datetime.timedelta(days=120)
    dates: List[datetime.date] = []

    # Pattern: Every Wednesday
    every_match = re.search(r"every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", lower)
    if every_match:
        target = WEEKDAY_MAP[every_match.group(1)]
        d = _next_weekday(today, target)
        while d <= horizon:
            dates.append(d)
            d += datetime.timedelta(days=7)
        return dates

    # Pattern: 1st and 3rd Wednesdays
    ordinal_weekday_match = re.search(
        r"(?:1st|first)\s+and\s+(?:3rd|third)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?",
        lower,
    )
    if ordinal_weekday_match:
        weekday = WEEKDAY_MAP[ordinal_weekday_match.group(1)]
        y, m = today.year, today.month
        while datetime.date(y, m, 1) <= horizon:
            first = _nth_weekday_of_month(y, m, weekday, 1)
            third = _nth_weekday_of_month(y, m, weekday, 3)
            for d in (first, third):
                if d and today <= d <= horizon:
                    dates.append(d)
            if m == 12:
                y += 1
                m = 1
            else:
                m += 1
        return sorted(dates)

    return []


def _article_to_events(article: Dict[str, Any], source_url: str) -> List[Dict[str, Any]]:
    title = str(article.get("title") or "").strip()
    body_html = str(article.get("body") or "")
    body_text = _strip_html(body_html)
    event_url = str(article.get("html_url") or source_url).strip()
    location_text = _extract_location(body_html)
    start_t, end_t = _parse_time_range(body_text)
    schedule_dates = _expand_schedule_dates(title, body_text)
    if not title or not schedule_dates:
        return []

    events: List[Dict[str, Any]] = []
    for event_date in schedule_dates:
        start_dt = EASTERN_TZ.localize(datetime.datetime.combine(event_date, start_t))
        end_dt = EASTERN_TZ.localize(datetime.datetime.combine(event_date, end_t))
        events.append(
            {
                "name": title,
                "description": body_text[:4000],
                "startDate": start_dt.isoformat(),
                "endTime": end_dt.isoformat(),
                "url": event_url,
                "status": "ACTIVE",
                "location": {
                    "name": "Thread Baltimore",
                    "address": location_text,
                },
                "imageUrl": "",
                "source": source_url,
            }
        )
    return events


def scrape_thread_helpcenter_events(api_url: str = THREAD_EVENTS_API_URL) -> List[Dict[str, Any]]:
    session = build_session()
    response = polite_get(session, api_url, timeout=30, allow_redirects=True)
    response.raise_for_status()
    payload = response.json()
    articles = payload.get("articles") if isinstance(payload, dict) else []
    if not isinstance(articles, list):
        return []

    events: List[Dict[str, Any]] = []
    seen = set()
    for article in articles:
        if not isinstance(article, dict):
            continue
        for event in _article_to_events(article, api_url):
            key = (event.get("name", "").strip().lower(), event.get("startDate", ""))
            if key in seen:
                continue
            seen.add(key)
            events.append(event)
    return events

