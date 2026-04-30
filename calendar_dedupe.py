import datetime
import json
import os


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
