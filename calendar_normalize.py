import datetime
import os
from io import BytesIO

import requests
from PIL import Image


def normalize_event_start_dates(events, get_start_dt, error_logger):
    for event in events:
        if "startDate" not in event:
            continue
        try:
            start_dt = get_start_dt(event)
            if start_dt is None:
                raise ValueError("Missing or invalid startDate")
            event["startDate"] = start_dt.isoformat()
        except Exception as e:
            print(f"Error converting datetime for event {event.get('name', 'Unknown')}: {e}")
            error_logger("normalize_datetime", e, context={"event_name": event.get("name", "Unknown")})


def download_event_images(events, sanitize_event_name, headers, error_logger):
    for event in events:
        if "imageUrl" not in event or not event["imageUrl"]:
            continue

        image_url = event["imageUrl"]
        safe_event_name = sanitize_event_name(event.get("name"))
        image_filename = f"event_images/{safe_event_name}.webp"

        event["imageUrl"] = "/" + image_filename
        if os.path.exists(image_filename):
            continue

        try:
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()

            img = Image.open(BytesIO(response.content))
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            img.save(image_filename, "WEBP", quality=80, method=6)

            print(f"Saved image: {image_filename}")
        except Exception as e:
            print(f"Failed to process image for event {event.get('name', 'Unknown')}: {e}")
            error_logger(
                "image_download",
                e,
                source_url=image_url,
                context={"event_name": event.get("name", "Unknown")},
            )
            event["imageUrl"] = image_url


def split_upcoming_events(events, get_start_dt, est_timezone):
    invalid_events = []
    nonerror_newevents = []
    time_now = datetime.datetime.now(est_timezone)
    today_date = time_now.date()

    for event in events:
        start_date = event.get("startDate")
        if not start_date:
            print(f"{event.get('name')} missing startdate ")
            event["invalid_reason"] = "missing startdate"
            invalid_events.append(event)
            continue

        start_date_time = get_start_dt(event)
        if start_date_time is None:
            event["invalid_reason"] = "invalid startdate"
            invalid_events.append(event)
            continue

        if (
            start_date_time.date() == datetime.date(2025, 6, 28)
            and "unity" not in event.get("name", "").lower()
        ):
            print(f"Skipping event on June 28, 2025: {event.get('name', 'Unknown')}")
            event["invalid_reason"] = "UNITY CONFLICT"
            invalid_events.append(event)
            continue

        if start_date_time.date() >= today_date:
            nonerror_newevents.append(event)
        else:
            event["invalid_reason"] = "Already happened"
            invalid_events.append(event)
            print(f"{event.get('name')} already happened ")

        if "Casual Coding" in event.get("name", ""):
            event["recurring"] = True

    return nonerror_newevents, invalid_events, today_date
