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

def fetch_calendar_events(ICS_URL, imageURL="https://www.unallocatedspace.org/wp-content/uploads/2017/03/UnallocatedLogoSmall.png", eventUrl = "https://www.unallocatedspace.org", recurring=True, preface="GameDevs "):
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
    
    return processICS(CACHE_FILENAME, imageURL, eventUrl, recurring, preface)

def processICS(CACHE_FILENAME, imageURL, eventUrl, recurring=True, preface="GameDevs "):
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
                is_recurring = ('rrule' in event or 'recurrence-id' in event) and recurring

                calendar_event = {
                    "id": event_id,
                    "name": preface + event_name,
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
    return calendar_events

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

if __name__ == "__main__":
    calendar_events = fetch_calendar_events(
        ICS_URL="https://baltimoreindiegames.com/events/list/?ical=1",
        imageURL="https://baltimoreindiegames.com/wp-content/uploads/2025/03/BIG_small.png",
        eventUrl="https://baltimoreindiegames.com/events/",
        recurring=False
    )

    print(f"\n✅ Final list of {len(calendar_events)} non-conflicting events:")
    for event in calendar_events:
        recurring_indicator = "🔄" if event.get('recurring') else "📅"
        print(f"{recurring_indicator} {event['name']} - {parse(event['startDate']).strftime('%Y-%m-%d %H:%M')}")