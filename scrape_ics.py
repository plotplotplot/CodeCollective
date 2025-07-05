import os
import requests
import recurring_ical_events  # pip install recurring-ical-events
from icalendar import Calendar  # pip install icalendar
from dateutil.parser import parse
import pytz
import hashlib
from datetime import datetime, timedelta
from pprint import pprint

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
        with open(CACHE_FILENAME, "wb") as f:
            f.write(r.content)  # Write as binary to preserve encoding
    else:
        print("✅ Using cached .ics file")
    
    return processICS(CACHE_FILENAME, existing_events, imageURL)

def processICS(CACHE_FILENAME, existing_events, imageURL, eventUrl):
    # Read the calendar file
    with open(CACHE_FILENAME, "rb") as f:
        calendar = Calendar.from_ical(f.read())

    today = datetime.now(TIMEZONE)
    future_cutoff = today + timedelta(days=180)  # 6 months ahead
    calendar_events = []

    print(f"\n📆 Processing calendar events between {today.date()} and {future_cutoff.date()}")

    # Use recurring-ical-events to get all events (including recurring ones)
    try:
        events = recurring_ical_events.of(calendar).between(today, future_cutoff)
        print(f"🔍 Found {len(events)} total events (including recurring instances)")
        
        for event in events:
            try:
                # Extract event details
                event_name = str(event.get('summary', 'Untitled Event'))
                event_start = event.get('dtstart')
                event_end = event.get('dtend')
                
                # Handle different datetime formats
                if hasattr(event_start, 'dt'):
                    start_dt = event_start.dt
                else:
                    start_dt = event_start
                    
                if hasattr(event_end, 'dt'):
                    end_dt = event_end.dt
                else:
                    end_dt = event_end
                
                # Convert to timezone-aware datetime if needed
                if not hasattr(start_dt, 'tzinfo') or start_dt.tzinfo is None:
                    start_dt = TIMEZONE.localize(start_dt)
                elif start_dt.tzinfo != TIMEZONE:
                    start_dt = start_dt.astimezone(TIMEZONE)
                    
                if not hasattr(end_dt, 'tzinfo') or end_dt.tzinfo is None:
                    end_dt = TIMEZONE.localize(end_dt)
                elif end_dt.tzinfo != TIMEZONE:
                    end_dt = end_dt.astimezone(TIMEZONE)

                print(f"\n🎯 Processing: {event_name}")
                print(f"   - Start: {start_dt}")
                print(f"   - End: {end_dt}")
                
                # Skip past events
                if end_dt < today:
                    print("   - Skipping: Event is in the past")
                    continue

                # Generate unique event ID
                event_id = hashlib.md5(
                    f"{event_name}{start_dt}{end_dt}".encode()
                ).hexdigest()[:16]

                # Check if this is a recurring event instance
                is_recurring = 'rrule' in event or 'recurrence-id' in event

                calendar_event = {
                    "id": event_id,
                    "name": event_name,
                    "startDate": start_dt.isoformat(),
                    "endTime": end_dt.isoformat(),
                    "description": str(event.get('description', '')),
                    "url": eventUrl,
                    "status": "ACTIVE",
                    "location": {
                        "name": str(event.get('location', '')),
                        "address": str(event.get('location', ''))
                    },
                    "imageUrl": imageURL,
                    "recurring": is_recurring
                }

                calendar_events.append(calendar_event)
                print(f"   - ✅ Added event (recurring: {is_recurring})")

            except Exception as e:
                print(f"⚠️ Error processing event: {e}")
                continue

    except Exception as e:
        print(f"❌ Error processing calendar with recurring-ical-events: {e}")
        print("🔄 Falling back to basic processing...")
        
        # Fallback to basic processing without recurring events
        for component in calendar.walk():
            if component.name == "VEVENT":
                try:
                    event_name = str(component.get('summary', 'Untitled Event'))
                    start_dt = component.get('dtstart').dt
                    end_dt = component.get('dtend').dt
                    
                    # Convert to timezone-aware datetime if needed
                    if not hasattr(start_dt, 'tzinfo') or start_dt.tzinfo is None:
                        start_dt = TIMEZONE.localize(start_dt)
                    elif start_dt.tzinfo != TIMEZONE:
                        start_dt = start_dt.astimezone(TIMEZONE)
                        
                    if not hasattr(end_dt, 'tzinfo') or end_dt.tzinfo is None:
                        end_dt = TIMEZONE.localize(end_dt)
                    elif end_dt.tzinfo != TIMEZONE:
                        end_dt = end_dt.astimezone(TIMEZONE)
                    
                    # Skip past events
                    if end_dt < today or start_dt > future_cutoff:
                        continue
                        
                    event_id = hashlib.md5(
                        f"{event_name}{start_dt}{end_dt}".encode()
                    ).hexdigest()[:16]

                    calendar_event = {
                        "id": event_id,
                        "name": event_name,
                        "startDate": start_dt.isoformat(),
                        "endTime": end_dt.isoformat(),
                        "description": str(component.get('description', '')),
                        "url": str(component.get('url', '')),
                        "status": "ACTIVE",
                        "location": {
                            "name": str(component.get('location', '')),
                            "address": str(component.get('location', ''))
                        },
                        "imageUrl": imageURL,
                        "recurring": False
                    }

                    calendar_events.append(calendar_event)
                    
                except Exception as e:
                    print(f"⚠️ Error processing fallback event: {e}")
                    continue

    print(f"\n📊 Found {len(calendar_events)} total events before filtering")
    return filter_events(existing_events, calendar_events)

def get_event_dates(events):
    dates = set()
    for event in events:
        try:
            event_date = parse(event["startDate"]).astimezone(TIMEZONE).date()
            dates.add(event_date)
        except Exception as e:  
            print(f"Error parsing date for event '{event.get('name', 'Unknown')}': {e}")
            continue
    return dates

def filter_events(existing_events, calendar_events):
    existing_dates = get_event_dates(existing_events)
    print(f"\n🗓️ Existing event dates: {sorted(existing_dates)}")

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
    for event in calendar_events:
        recurring_indicator = "🔄" if event.get('recurring') else "📅"
        print(f"{recurring_indicator} {event['name']} - {parse(event['startDate']).strftime('%Y-%m-%d %H:%M')}")