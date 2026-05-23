import datetime
import json
import os

from dateutil.parser import parse


RECURRING_MANUAL_LOOKAHEAD_DAYS = 366
WEEKDAY_NAME_TO_INDEX = {
    "MO": 0,
    "MON": 0,
    "MONDAY": 0,
    "TU": 1,
    "TUE": 1,
    "TUESDAY": 1,
    "WE": 2,
    "WED": 2,
    "WEDNESDAY": 2,
    "TH": 3,
    "THU": 3,
    "THURSDAY": 3,
    "FR": 4,
    "FRI": 4,
    "FRIDAY": 4,
    "SA": 5,
    "SAT": 5,
    "SATURDAY": 5,
    "SU": 6,
    "SUN": 6,
    "SUNDAY": 6,
}


def _nth_weekday_of_month(year, month, weekday, n):
    first = datetime.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + datetime.timedelta(days=offset + (n - 1) * 7)


def _last_weekday_of_month(year, month, weekday):
    if month == 12:
        next_month_first = datetime.date(year + 1, 1, 1)
    else:
        next_month_first = datetime.date(year, month + 1, 1)
    last = next_month_first - datetime.timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - datetime.timedelta(days=offset)


def _observed_holiday(day):
    if day.weekday() == 5:  # Saturday
        return day - datetime.timedelta(days=1)
    if day.weekday() == 6:  # Sunday
        return day + datetime.timedelta(days=1)
    return day


def us_bank_holidays_10(year):
    # Classic 10 U.S. bank holidays (excludes Juneteenth).
    new_year = datetime.date(year, 1, 1)
    independence = datetime.date(year, 7, 4)
    veterans = datetime.date(year, 11, 11)
    christmas = datetime.date(year, 12, 25)
    return {
        new_year,
        _observed_holiday(new_year),
        _nth_weekday_of_month(year, 1, 0, 3),                     # MLK Day
        _nth_weekday_of_month(year, 2, 0, 3),                     # Presidents Day
        _last_weekday_of_month(year, 5, 0),                       # Memorial Day
        independence,
        _observed_holiday(independence),
        _nth_weekday_of_month(year, 9, 0, 1),                     # Labor Day
        _nth_weekday_of_month(year, 10, 0, 2),                    # Columbus Day
        veterans,
        _observed_holiday(veterans),
        _nth_weekday_of_month(year, 11, 3, 4),                    # Thanksgiving
        christmas,
        _observed_holiday(christmas),
    }


def _normalize_weekday(value):
    if isinstance(value, int) and 0 <= value <= 6:
        return value

    if isinstance(value, str):
        normalized = value.strip().upper()
        return WEEKDAY_NAME_TO_INDEX.get(normalized)

    return None


def _coerce_positive_int(value, default):
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced > 0 else default


def _parse_recurrence_until(value):
    if not value:
        return None
    try:
        parsed = parse(str(value))
    except Exception:
        return None
    return parsed.date()


def _event_duration(event, base_start):
    end_raw = event.get("endTime")
    if not end_raw:
        return datetime.timedelta(hours=2)

    parsed_end = parse(end_raw)
    if parsed_end.tzinfo is None:
        parsed_end = parsed_end.replace(tzinfo=base_start.tzinfo)
    return parsed_end - base_start


def _normalize_recurrence_config(event, base_start):
    recurrence = event.get("recurrence")
    if not recurrence and event.get("recurring"):
        recurrence = {"freq": "weekly"}

    if not isinstance(recurrence, dict):
        return None

    freq = str(recurrence.get("freq") or "weekly").strip().lower()
    if freq != "weekly":
        return None

    byweekday_raw = recurrence.get("byweekday") or [base_start.weekday()]
    byweekday = []
    for value in byweekday_raw:
        normalized = _normalize_weekday(value)
        if normalized is not None and normalized not in byweekday:
            byweekday.append(normalized)
    if not byweekday:
        byweekday = [base_start.weekday()]

    exclude_dates = set()
    for value in recurrence.get("exclude_dates", []) or []:
        parsed = _parse_recurrence_until(value)
        if parsed is not None:
            exclude_dates.add(parsed)

    return {
        "freq": freq,
        "interval": _coerce_positive_int(recurrence.get("interval"), 1),
        "byweekday": byweekday,
        "until": _parse_recurrence_until(recurrence.get("until")),
        "skip_bank_holidays": bool(recurrence.get("skip_bank_holidays")),
        "exclude_dates": exclude_dates,
    }


def _build_manual_recurrence_instances(event, today_date, end_date):
    start_raw = event.get("startDate")
    if not start_raw:
        return [event]

    try:
        base_start = parse(start_raw)
        if base_start.tzinfo is None:
            return [event]

        recurrence = _normalize_recurrence_config(event, base_start)
        if recurrence is None:
            return [event]

        duration = _event_duration(event, base_start)
        until_date = recurrence["until"] or end_date
        window_end = min(until_date, end_date)
        if window_end < today_date:
            return []

        week_anchor = base_start.date() - datetime.timedelta(days=base_start.weekday())
        window_start = max(today_date, base_start.date())
        candidate_date = window_start
        expanded = []
        while candidate_date <= window_end:
            weeks_since_anchor = (candidate_date - week_anchor).days // 7
            if (
                candidate_date >= base_start.date()
                and candidate_date.weekday() in recurrence["byweekday"]
                and weeks_since_anchor % recurrence["interval"] == 0
                and candidate_date not in recurrence["exclude_dates"]
            ):
                if recurrence["skip_bank_holidays"] and candidate_date in us_bank_holidays_10(candidate_date.year):
                    candidate_date += datetime.timedelta(days=1)
                    continue

                instance_start = datetime.datetime.combine(candidate_date, base_start.timetz())
                instance = dict(event)
                if event.get("id"):
                    instance["id"] = f"{event['id']}__{candidate_date.isoformat()}"
                instance["startDate"] = instance_start.isoformat()
                instance["endTime"] = (instance_start + duration).isoformat()
                instance["recurring"] = True
                expanded.append(instance)
            candidate_date += datetime.timedelta(days=1)
        return expanded
    except Exception:
        return [event]


def expand_manual_recurring_events(existing_events, today_date):
    expanded = []
    end_date = today_date + datetime.timedelta(days=RECURRING_MANUAL_LOOKAHEAD_DAYS)

    for event in existing_events:
        if not event.get("recurring") and not event.get("recurrence"):
            expanded.append(event)
            continue

        expanded.extend(_build_manual_recurrence_instances(event, today_date, end_date))

    return expanded


def merge_and_dedupe_events(
    city,
    nonerror_newevents,
    invalid_events,
    today_date,
    get_start_dt,
    normalize_event_text,
    find_existing_duplicate,
    choose_preferred_duplicate,
    apply_geocode_cache,
    geocode_cache,
):
    def get_event_signature_strict(event):
        e2 = event.copy()
        e2.pop("scrapeTime", None)
        return json.dumps(e2, sort_keys=True)

    def get_event_signature(event):
        name = normalize_event_text(event.get("name", ""))
        start_dt = get_start_dt(event)
        if not start_dt:
            return name
        return f"{name}||{start_dt.date().isoformat()}||{start_dt.hour:02d}"

    unique_events = []
    date_occupied = set()

    with open(os.path.join(city, "manual_events.json"), "r", encoding="utf-8") as f:
        existing_events_in_file = json.load(f)

    existing_events_in_file = expand_manual_recurring_events(existing_events_in_file, today_date)

    upcoming_existing_events_in_file = []
    for event in existing_events_in_file:
        start_dt = get_start_dt(event)
        if start_dt is None:
            continue
        if start_dt.date() >= today_date:
            upcoming_existing_events_in_file.append(event)

    total_events = []
    for event in nonerror_newevents:
        existing_duplicate = find_existing_duplicate(event, upcoming_existing_events_in_file)
        if existing_duplicate is None:
            total_events.append(event)
        else:
            event["invalid_reason"] = "Already exists in manual events"
            invalid_events.append(event)

    total_events += upcoming_existing_events_in_file
    cache_updated = apply_geocode_cache(total_events, geocode_cache)

    for event in total_events:
        if event.get("recurring"):
            continue

        if not event.get("scrapeTime"):
            event["scrapeTime"] = str(datetime.datetime.now())

        try:
            start_dt = get_start_dt(event)
            if start_dt is None:
                raise ValueError("invalid startDate")
            event_date = start_dt.date()
        except Exception:
            event["invalid_reason"] = "Bad startdate"
            invalid_events.append(event)
            continue

        existing_event = find_existing_duplicate(event, unique_events)
        if existing_event:
            if get_event_signature_strict(existing_event) != get_event_signature_strict(event):
                preferred_event, rejected_event = choose_preferred_duplicate(existing_event, event)
                unique_events.remove(existing_event)
                unique_events.append(preferred_event)
                invalid_events.append(rejected_event)
            else:
                event["invalid_reason"] = "Already exists with same normalized content"
                invalid_events.append(event)
            continue

        unique_events.append(event)
        date_occupied.add(event_date)

    for event in total_events:
        if not event.get("recurring"):
            continue

        if "Member Meeting" in event.get("name", ""):
            event["invalid_reason"] = "Member meeting"
            invalid_events.append(event)
            continue

        if not event.get("scrapeTime"):
            event["scrapeTime"] = str(datetime.datetime.now())

        try:
            start_dt = get_start_dt(event)
            if start_dt is None:
                raise ValueError("invalid startDate")
            event_date = start_dt.date()
        except Exception:
            event["invalid_reason"] = "Invalid date"
            invalid_events.append(event)
            continue

        existing_event = find_existing_duplicate(event, unique_events)
        # Restriction disabled: allow recurring events to appear even when
        # non-recurring events already occupy the same date.
        # if event_date not in date_occupied and existing_event is None:
        if existing_event is None:
            unique_events.append(event)
        else:
            event["invalid_reason"] = "Recurring event removed when a stronger conflicting event is present"
            invalid_events.append(event)

    unique_events.sort(
        key=lambda e: get_start_dt(e) or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
    )

    sorted_events = sorted(
        (e for e in unique_events if "startDate" in e),
        key=lambda e: get_start_dt(e) or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc),
    )

    return sorted_events, invalid_events, bool(cache_updated)
