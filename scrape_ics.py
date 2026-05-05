import os
import requests
import recurring_ical_events  # pip install recurring-ical-events
from icalendar import Calendar  # pip install icalendar
from dateutil.parser import parse
import pytz
import hashlib
from datetime import date, datetime, time, timedelta
from pprint import pprint

# Constants
TIMEZONE = pytz.timezone("America/New_York")
CACHE_MAX_AGE = timedelta(days=1)
import re, urllib.parse


import re
from http_client import build_session, polite_get


def _looks_like_ics_bytes(payload):
    if not payload:
        return False
    sample = payload[:4096].decode("utf-8", errors="ignore").lstrip("\ufeff\r\n\t ").upper()
    return "BEGIN:VCALENDAR" in sample


def _read_valid_cached_ics(cache_filename):
    if not os.path.exists(cache_filename):
        return None

    with open(cache_filename, "rb") as f:
        payload = f.read()

    return payload if _looks_like_ics_bytes(payload) else None

def fetch_calendar_events(ICS_URL, city, imageURL="https://www.unallocatedspace.org/wp-content/uploads/2017/03/UnallocatedLogoSmall.png", eventUrl="https://www.unallocatedspace.org", recurring=True, preface="GameDevs "):
    """Fetch and return calendar events in the standardized format."""
    print(f"Fetching ICS from {ICS_URL}")
    fetch_from_web = True
    os.makedirs(city, exist_ok=True)

    # Always prefer https
    ICS_URL = re.sub(r"^http://", "https://", ICS_URL.strip())
    url = ICS_URL
    parsed_url = urllib.parse.urlsplit(url if '://' in url else 'https://' + url)
    host_token = re.sub(r'[^A-Za-z0-9._-]+', '_', (parsed_url.hostname or '').split('.', 1)[0]).strip('._-') or 'file'
    url_hash = hashlib.md5(ICS_URL.encode("utf-8")).hexdigest()[:10]
    token = f"{host_token}_{url_hash}"

    CACHE_FILENAME = os.path.join(city, f"cache_{token}.ics")

    cached_payload = None

    # Check if cached file exists and is recent
    if os.path.exists(CACHE_FILENAME):
        mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_FILENAME))
        if datetime.now() - mtime < CACHE_MAX_AGE:
            cached_payload = _read_valid_cached_ics(CACHE_FILENAME)
            if cached_payload is not None:
                fetch_from_web = False
            else:
                print("⚠️ Cached ICS file is invalid, refetching...")

    if fetch_from_web:
        print("🔄 Downloading new .ics file from URL...")

        session = build_session(
            user_agent="CodeCollectiveBot/1.0 (+https://github.com/juliancoy/CodeCollective)",
            retries=3,
            backoff_factor=1.0,
        )
        session.headers.update({
            "Accept": "text/calendar, text/plain, */*",
            # Referer helps with some WAFs that block direct hotlinks to feeds
            "Referer": "https://wvbusinesslink.com/events/month/?hide_subsequent_recurrences=1",
        })

        # Warm-up visit to set cookies (HTML page, not the ICS endpoint)
        try:
            warmup_url = "https://wvbusinesslink.com/events/month/?hide_subsequent_recurrences=1"
            polite_get(session, warmup_url, timeout=15, allow_redirects=True)
        except Exception as e:
            print(f"⚠️ Warm-up fetch failed (continuing): {e}")

        # Now fetch the ICS
        r = polite_get(session, ICS_URL, timeout=30, allow_redirects=True)
        if r.status_code == 403:
            # One more try without the Referer (some configs flip this)
            headers_no_ref = session.headers.copy()
            headers_no_ref.pop("Referer", None)
            r = polite_get(session, ICS_URL, timeout=30, allow_redirects=True, headers=headers_no_ref)

        # If still blocked, surface helpful debug info
        if r.status_code >= 400:
            print("🚫 Request blocked. Debug headers:")
            print("   - Status:", r.status_code)
            print("   - Content-Type:", r.headers.get("Content-Type"))
            print("   - Server:", r.headers.get("Server"))
            print("   - CF-Ray:", r.headers.get("CF-Ray"))
            print("   - Excerpt:", r.text[:200])
            r.raise_for_status()

        # Basic sanity check
        ct = (r.headers.get("Content-Type") or "").lower()
        if "text/calendar" not in ct and not ICS_URL.endswith(".ics"):
            print(f"⚠️ Unexpected content type for ICS: {ct}")

        if not _looks_like_ics_bytes(r.content):
            excerpt = r.text[:200].replace("\n", " ")
            raise ValueError(f"Downloaded payload is not a valid ICS calendar: {excerpt}")

        with open(CACHE_FILENAME, "wb") as f:
            f.write(r.content)  # keep exact bytes
    else:
        print("✅ Using cached .ics file")

    return processICS(CACHE_FILENAME, imageURL, eventUrl, recurring, preface)
def _extract_image_url_from_component(component):
    """
    Try to extract an image URL from ATTACH properties.
    Supports single or multiple ATTACH lines, with or without FMTTYPE.
    Returns the first image-looking URL or None.
    """
    def looks_like_image(url: str) -> bool:
        url_l = url.lower()
        return url_l.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")) or "/image" in url_l

    attach = component.get('attach')
    if not attach:
        return None

    # icalendar may return a list or a single vUri-like object
    candidates = attach if isinstance(attach, list) else [attach]

    # Prefer ATTACH items with FMTTYPE starting with image/
    image_first = None
    for a in candidates:
        try:
            url = str(a)
        except Exception:
            continue
        fmt = None
        try:
            # a.params is available on icalendar.vUri / vText
            fmt = a.params.get('FMTTYPE')
        except Exception:
            pass

        if fmt and str(fmt).lower().startswith("image/"):
            return url  # strongest match
        if image_first is None and looks_like_image(url):
            image_first = url

    return image_first


def _normalize_component_datetime(value, timezone, is_end=False):
    if isinstance(value, datetime):
        normalized = value
    elif isinstance(value, date):
        default_time = time.max if is_end else time.min
        normalized = datetime.combine(value, default_time)
    else:
        raise TypeError(f"Unsupported ICS datetime value: {type(value).__name__}")

    if normalized.tzinfo is None:
        return timezone.localize(normalized)
    if normalized.tzinfo != timezone:
        return normalized.astimezone(timezone)
    return normalized

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
                start_dt = event_start.dt if hasattr(event_start, 'dt') else event_start
                end_dt = event_end.dt if hasattr(event_end, 'dt') else event_end
                
                # Convert to timezone-aware datetime if needed
                start_dt = _normalize_component_datetime(start_dt, TIMEZONE)
                end_dt = _normalize_component_datetime(end_dt, TIMEZONE, is_end=True)

                print(f"\n🎯 Processing: {event_name}")
                print(f"   - Start: {start_dt}")
                print(f"   - End: {end_dt}")
                
                # Skip past events
                if end_dt < today:
                    print("   - Skipping: Event is in the past")
                    continue

                # Generate unique event ID
                event_id = hashlib.md5(f"{event_name}{start_dt}{end_dt}".encode()).hexdigest()[:16]

                # Recurrence flag
                is_recurring = ('rrule' in event or 'recurrence-id' in event) and recurring

                # Prefer event's own URL if present
                event_page_url = str(event.get('url', eventUrl))

                # Try to pull an image from ATTACH; fall back to provided default
                image_from_attach = _extract_image_url_from_component(event)
                final_image_url = image_from_attach or imageURL
                if image_from_attach:
                    print(f"   - Found image via ATTACH: {final_image_url}")

                calendar_event = {
                    "id": event_id,
                    "name": preface + event_name,
                    "startDate": start_dt.isoformat(),
                    "endTime": end_dt.isoformat(),
                    "description": str(event.get('description', '')),
                    "url": event_page_url,
                    "status": "ACTIVE",
                    "location": {
                        "name": str(event.get('location', '')),
                        "address": str(event.get('location', ''))
                    },
                    "imageUrl": final_image_url,
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
                    start_dt = _normalize_component_datetime(start_dt, TIMEZONE)
                    end_dt = _normalize_component_datetime(end_dt, TIMEZONE, is_end=True)
                    
                    # Skip outside window
                    if end_dt < today or start_dt > future_cutoff:
                        continue
                        
                    event_id = hashlib.md5(f"{event_name}{start_dt}{end_dt}".encode()).hexdigest()[:16]

                    # Prefer event's own URL if present
                    event_page_url = str(component.get('url', '')) or eventUrl

                    # Try ATTACH here too
                    image_from_attach = _extract_image_url_from_component(component)
                    final_image_url = image_from_attach or imageURL
                    if image_from_attach:
                        print(f"   - Found image via ATTACH (fallback): {final_image_url}")

                    calendar_event = {
                        "id": event_id,
                        "name": preface + event_name,
                        "startDate": start_dt.isoformat(),
                        "endTime": end_dt.isoformat(),
                        "description": str(component.get('description', '')),
                        "url": event_page_url,
                        "status": "ACTIVE",
                        "location": {
                            "name": str(component.get('location', '')),
                            "address": str(component.get('location', ''))
                        },
                        "imageUrl": final_image_url,
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
        city="baltimore",
        preface="",
        recurring=False
    )

    print(f"\n✅ Final list of {len(calendar_events)} non-conflicting events:")
    for event in calendar_events:
        recurring_indicator = "🔄" if event.get('recurring') else "📅"
        print(f"{recurring_indicator} {event['name']} - {parse(event['startDate']).strftime('%Y-%m-%d %H:%M')} | image: {event['imageUrl']}")
