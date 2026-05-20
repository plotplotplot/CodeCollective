import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytz
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date

from http_client import build_session, polite_get


EASTERN_TZ = pytz.timezone("America/New_York")

_DATE_TIME_RE = re.compile(
    r"^(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},\s+\d{4}"
    r"(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?"
    r"(?:\s*[-–]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?"
    r"$",
    re.IGNORECASE,
)
_DATE_ONLY_RE = re.compile(
    r"(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},\s+\d{4}",
    re.IGNORECASE,
)

_SKIP_TITLE_RE = re.compile(
    r"^(?:recording link|respondents:?|location:?|cancelled|virtual event.*|kick off speaker:?)$",
    re.IGNORECASE,
)
_SECTION_TITLE_RE = re.compile(
    r"(baltimore community trivia|issue brief|convening|summit|webinar|topic-focused)",
    re.IGNORECASE,
)


def _clean_lines(soup: BeautifulSoup) -> List[str]:
    return [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]


def _is_datetime_line(text: str) -> bool:
    return bool(_DATE_TIME_RE.match(text.strip()))


def _find_title(lines: List[str], index: int) -> str:
    for candidate in reversed(lines[max(0, index - 12) : index]):
        normalized = candidate.strip()
        if not normalized or _is_datetime_line(normalized):
            continue
        if _SECTION_TITLE_RE.search(normalized):
            return normalized

    candidates: List[str] = []
    for candidate in reversed(lines[max(0, index - 8) : index]):
        normalized = candidate.strip()
        if not normalized:
            continue
        if _is_datetime_line(normalized):
            continue
        if _SKIP_TITLE_RE.match(normalized):
            continue
        if len(normalized) < 4:
            continue
        candidates.append(normalized)
    if not candidates:
        return ""

    def score(value: str) -> int:
        low = value.lower()
        s = 0
        if "#" in value:
            s += 4
        if any(token in low for token in ("trivia", "convening", "summit", "webinar", "issue brief", "session")):
            s += 4
        if any(token in low for token in ("speaker", "respondents", "recording link")):
            s -= 5
        if "," in value and not any(token in low for token in ("trivia", "convening", "summit", "webinar", "issue brief", "session")):
            s -= 3
        if re.search(r"\d{1,6}\s+\w+", value):
            s -= 3
        if "," in value and any(ch.isdigit() for ch in value):
            s -= 2
        return s

    return sorted(candidates, key=lambda item: score(item), reverse=True)[0]


def _extract_time_range(raw: str) -> Tuple[Optional[str], Optional[str]]:
    range_match = re.search(
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
        raw,
        flags=re.IGNORECASE,
    )
    if range_match:
        return range_match.group(1), range_match.group(2)

    short_range_match = re.search(
        r"\b(\d{1,2}(?::\d{2})?)\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b",
        raw,
        flags=re.IGNORECASE,
    )
    if short_range_match:
        return short_range_match.group(1), short_range_match.group(2)

    single_match = re.search(r"\bat\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", raw, flags=re.IGNORECASE)
    if single_match:
        return single_match.group(1), None

    no_at_single = re.search(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", raw, flags=re.IGNORECASE)
    if no_at_single:
        return no_at_single.group(1), None

    return None, None


def _parse_start_end(raw_line: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    try:
        date_match = _DATE_ONLY_RE.search(raw_line)
        if not date_match:
            return None, None
        date_only = parse_date(date_match.group(0), fuzzy=True, default=datetime(2000, 1, 1, 0, 0, 0))
    except Exception:
        return None, None

    start_time_str, end_time_str = _extract_time_range(raw_line)
    if start_time_str:
        def parse_parts(token: str) -> Tuple[int, int, Optional[str]]:
            token = token.strip().lower()
            m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", token)
            if not m:
                raise ValueError(f"invalid time token: {token}")
            return int(m.group(1)), int(m.group(2) or "0"), m.group(3)

        def to_24h(hour: int, meridiem: str) -> int:
            if meridiem == "am":
                return 0 if hour == 12 else hour
            if meridiem == "pm":
                return 12 if hour == 12 else hour + 12
            raise ValueError("missing meridiem")

        sh, sm, sap = parse_parts(start_time_str)
        eh = em = 0
        eap: Optional[str] = None
        if end_time_str:
            eh, em, eap = parse_parts(end_time_str)

        if not sap:
            if eap == "am":
                sap = "am"
            elif eap == "pm":
                if sh == 12 or sh < eh:
                    sap = "pm"
                else:
                    sap = "am"
            else:
                sap = "pm" if 8 <= sh <= 11 else "am"

        start_dt = date_only.replace(hour=to_24h(sh, sap), minute=sm, second=0, microsecond=0)
    else:
        start_dt = date_only.replace(hour=12, minute=0, second=0, microsecond=0)

    if end_time_str:
        eh, em, eap = parse_parts(end_time_str)
        if not eap:
            _, _, sap = parse_parts(start_time_str)
            eap = sap or "pm"
        end_dt = date_only.replace(hour=to_24h(eh, eap), minute=em, second=0, microsecond=0)
    else:
        end_dt = start_dt + timedelta(hours=2)

    if start_dt.tzinfo is None:
        start_dt = EASTERN_TZ.localize(start_dt)
    if end_dt.tzinfo is None:
        end_dt = EASTERN_TZ.localize(end_dt)
    return start_dt, end_dt


def _extract_location(lines: List[str], index: int) -> str:
    window = lines[index : min(len(lines), index + 8)]
    for idx, line in enumerate(window):
        if re.match(r"^location:?\s*$", line, flags=re.IGNORECASE):
            for follow in window[idx + 1 :]:
                if not follow or _is_datetime_line(follow):
                    break
                if _SKIP_TITLE_RE.match(follow):
                    continue
                return follow.strip()
        location_inline = re.match(r"^location:\s*(.+)$", line, flags=re.IGNORECASE)
        if location_inline:
            return location_inline.group(1).strip()
    return ""


def scrape_bniajfi_community_change_events(source_url: str) -> List[Dict[str, Any]]:
    session = build_session()
    response = polite_get(session, source_url, timeout=30, allow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    lines = _clean_lines(soup)

    events: List[Dict[str, Any]] = []
    seen = set()

    for i, line in enumerate(lines):
        if not _is_datetime_line(line):
            continue
        title = _find_title(lines, i)
        if not title:
            continue

        start_dt, end_dt = _parse_start_end(line)
        if not start_dt:
            continue
        key = (title.lower(), start_dt.isoformat())
        if key in seen:
            continue
        seen.add(key)

        status = "CANCELLED" if any(
            re.match(r"^cancelled$", probe, flags=re.IGNORECASE)
            for probe in lines[i : min(len(lines), i + 3)]
        ) else "ACTIVE"

        location_text = _extract_location(lines, i)
        events.append(
            {
                "name": title,
                "description": "",
                "startDate": start_dt.isoformat(),
                "endTime": end_dt.isoformat() if end_dt else "",
                "url": source_url,
                "status": status,
                "location": {
                    "name": "Baltimore Neighborhood Indicators Alliance",
                    "address": location_text,
                },
                "imageUrl": "",
                "source": source_url,
            }
        )

    return events
