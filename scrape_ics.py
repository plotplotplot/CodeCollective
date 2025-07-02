import os
import requests
from ics import Calendar
from dateutil.parser import parse
import pytz
import hashlib
from datetime import datetime, timedelta

# Constants
TIMEZONE = pytz.timezone("America/New_York")
CACHE_MAX_AGE = timedelta(days=1)

def fetch_calendar_events(existing_events, ICS_URL, imageURL="https://www.unallocatedspace.org/wp-content/uploads/2017/03/UnallocatedLogoSmall.png"):
    """Fetch and return calendar events in the standardized format."""
    fetch_from_web = True
    CACHE_FILENAME = f"cache_{hashlib.md5(ICS_URL.encode()).hexdigest()}.ics"

    # Check if cached file exists and is recent
    if os.path.exists(CACHE_FILENAME):
        mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_FILENAME))
        if datetime.now() - mtime < CACHE_MAX_AGE:
            fetch_from_web = False

    if fetch_from_web:
        print("🔄 Downloading new .ics file from URL...")
        r = requests.get(ICS_URL)
        r.raise_for_status()
        with open(CACHE_FILENAME, "w", encoding="utf-8") as f:
            f.write(r.text)
    else:
        print("✅ Using cached .ics file")
    processICS(CACHE_FILENAME, existing_events, imageURL)

def processICS(CACHE_FILENAME, existing_events, imageURL="https://www.unallocatedspace.org/wp-content/uploads/2017/03/UnallocatedLogoSmall.png"):
    # Read from the cached file
    with open(CACHE_FILENAME, "r", encoding="utf-8") as f:
        calendar = Calendar(f.read())

    today = datetime.now(TIMEZONE).date()
    calendar_events = []

    for event in calendar.events:
        try:
            start_time = event.begin.astimezone(TIMEZONE)
            end_time = event.end.astimezone(TIMEZONE)

            if start_time.date() < today:
                #print(f"⏭️ Skipping past event '{event.name}' on {start_time.date()}")
                continue
            print(f"📅 Processing event '{event.name}' from {start_time} to {end_time}")
            event_id = hashlib.md5(
                f"{event.name}{event.begin}{event.end}".encode()
            ).hexdigest()[:16]

            calendar_event = {
                "id": event_id,
                "name": str(event.name) if event.name else "Untitled Event",
                "startDate": start_time.isoformat(),
                "endTime": end_time.isoformat(),
                "description": str(event.description) if event.description else "",
                "url": str(event.url) if event.url else "",
                "status": "ACTIVE",
                "location": {
                    "name": str(event.location) if event.location else "",
                    "address": str(event.location) if event.location else ""
                },
                "imageUrl": imageURL
            }

            calendar_events.append(calendar_event)

        except Exception as e:
            print(f"⚠️ Error processing event '{getattr(event, 'name', 'Unknown')}': {e}")
            continue

    return filter_events(existing_events, calendar_events)

def get_event_dates(events):
    dates = set()
    for event in events:
        try:
            dates.add(parse(event["startDate"]).astimezone(TIMEZONE).date())
        except Exception as e:  
            print(f"Error parsing date for event '{event.get('name', 'Unknown')}': {e}")
            continue
    return dates

def filter_events(existing_events, calendar_events):
    existing_dates = get_event_dates(existing_events)

    non_conflicting = []
    for event in calendar_events:
        event_date = parse(event["startDate"]).astimezone(TIMEZONE).date()
        if event_date in existing_dates:
            print(f"🔴 Skipping calendar event '{event['name']}' on {event_date} - Conflict with existing")
        else:
            print(f"🟢 Adding calendar event '{event['name']}' on {event_date} - No conflict")
            non_conflicting.append(event)

    return non_conflicting

if __name__ == "__main__":
    existing_events = [
        {
            "id": "77ffd88ad65d41b6",
            "name": "Evening With ESOs",
            "startDate": "2025-06-10T18:00:00-04:00",
            "endTime": "2025-06-10T20:00:00-04:00",
            "description": "Equitech Tuesday event at GBC Offices: Evening With ESOs. Join Baltimore's tech ecosystem for networking and innovation.",
            "url": "https://upsurgebaltimore.com/equitech-tuesday/",
            "status": "ACTIVE",
            "location": {
                "name": "GBC Offices",
                "address": "GBC Offices, Baltimore, MD 21202",
                "city": "Baltimore",
                "state": "MD",
                "country": "US"
            },
            "imageUrl": "/event_images/Evening_With_ESOs.webp"
        }
    ]

    ICS_URL = "https://calendar.google.com/calendar/ical/unallocatedspacehq@gmail.com/public/basic.ics"
    print("📅 Fetching calendar events...")
    calendar_events = fetch_calendar_events(existing_events, ICS_URL)

    print(f"\n✅ Final list of {len(calendar_events)} non-conflicting events:")
    #from pprint import pprint
    #pprint(calendar_events)
