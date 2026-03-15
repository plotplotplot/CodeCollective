import scrape_meetup
import scrape_eventbrite
import scrape_jotform
import scrape_luma
import scrape_ics
import scrape_gform
import scrape_luma_orgpage
import scrape_luma_calendar
import scrape_luma_user
import scrape_mtc
import scrape_gdg
import tag_rules
import json
import datetime
import pytz
from bs4 import BeautifulSoup
import re
import scrape_eventbrite_org
import markdown
from dateutil.parser import parse
import sys
import importlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
import genSimpleCalendar
from events_map_generator import generate_events_map_page
from geocode_cache import (
    load_geocode_cache,
    save_geocode_cache,
    apply_geocode_cache,
    normalize_address,
)
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import unicodedata
from urllib.parse import parse_qs, urlparse

# Define the timezone for EST
est_timezone = pytz.timezone("America/New_York")

SOURCE_KIND_CONCURRENCY = {
    "meetup": 1,
    "eventbrite_org": 1,
    "eventbrite_event": 2,
    "luma_org": 2,
    "luma_calendar": 2,
    "luma_user": 2,
    "luma_event": 3,
    "jotform": 3,
    "google_form": 3,
    "gdg": 3,
    "unknown": 2,
}


def merge_tags(*tag_lists):
    merged = []
    seen = set()

    for tag_list in tag_lists:
        if not tag_list:
            continue
        for tag in tag_list:
            if not tag:
                continue
            if tag in seen:
                continue
            seen.add(tag)
            merged.append(tag)

    return merged


def normalize_source_entry(entry, legacy_kind=None):
    if isinstance(entry, dict):
        normalized = dict(entry)
        normalized.setdefault("url", "")
        normalized["tags"] = list(normalized.get("tags") or [])
        return normalized

    if legacy_kind == "Luma Users" and isinstance(entry, str) and not entry.startswith("http"):
        return {
            "url": f"https://api.lu.ma/user/profile/events-hosting?user_api_id={entry}",
            "tags": [],
            "user_api_id": entry,
        }

    if isinstance(entry, str):
        return {"url": entry, "tags": []}

    if isinstance(entry, int) and legacy_kind == "GDGChapters":
        return {
            "url": f"https://gdg.community.dev/chapter/{entry}",
            "tags": [],
            "chapter_id": entry,
        }

    return {"url": str(entry), "tags": []}


def flatten_sources(raw_sources):
    if isinstance(raw_sources, list):
        return [normalize_source_entry(entry) for entry in raw_sources]

    flattened = []
    for legacy_kind, entries in (raw_sources or {}).items():
        for entry in entries:
            normalized = normalize_source_entry(entry, legacy_kind=legacy_kind)
            normalized.setdefault("legacy_kind", legacy_kind)
            flattened.append(normalized)
    return flattened


def infer_source_kind(source_url):
    if not source_url:
        return None

    parsed = urlparse(source_url)
    host = parsed.netloc.lower()
    path = parsed.path or ""
    segments = [segment for segment in path.split("/") if segment]

    if "meetup.com" in host:
        return "meetup"

    if "eventbrite." in host:
        if path.startswith("/o/") or path.startswith("/cc/"):
            return "eventbrite_org"
        return "eventbrite_event"

    if "jotform.com" in host:
        return "jotform"

    if (host == "forms.gle") or (host == "docs.google.com" and "/forms/" in path):
        return "google_form"

    if host == "api.lu.ma" and path == "/user/profile/events-hosting":
        return "luma_user"

    if host in {"lu.ma", "luma.com"}:
        if path.startswith("/calendar/"):
            return "luma_calendar"
        if path.startswith("/user/"):
            return "luma_org"
        if len(segments) == 1 and re.fullmatch(r"[A-Za-z0-9]{8}", segments[0]):
            return "luma_event"
        if len(segments) == 1:
            return "luma_org"

    if "gdg.community.dev" in host:
        return "gdg"

    return None


def extract_luma_user_id(source):
    if source.get("user_api_id"):
        return source["user_api_id"]

    parsed = urlparse(source.get("url", ""))
    query = parse_qs(parsed.query)
    values = query.get("user_api_id")
    return values[0] if values else None


def extract_gdg_chapter_id(source):
    if source.get("chapter_id"):
        return source["chapter_id"]

    match = re.search(r"/chapter/(\d+)", source.get("url", ""))
    if match:
        return int(match.group(1))

    return None


def coerce_events(payload):
    if not payload:
        return []
    if isinstance(payload, list):
        return [event for event in payload if isinstance(event, dict) and not event.get("error")]
    if isinstance(payload, dict):
        return [] if payload.get("error") else [payload]
    return []


def apply_source_metadata(events, source):
    normalized_events = coerce_events(events)
    source_url = source.get("url", "")
    source_tags = source.get("tags", [])

    for event in normalized_events:
        event["tags"] = merge_tags(source_tags, event.get("tags"))
        if source_url:
            event.setdefault("source", source_url)
            event["source_url"] = source_url

    return normalized_events


def source_pattern_details(source):
    parsed = urlparse(source.get("url", ""))
    segments = [segment for segment in parsed.path.split("/") if segment]
    return {
        "url": source.get("url", ""),
        "host": parsed.netloc.lower(),
        "path": parsed.path,
        "path_segments": segments,
    }


def build_error_entry(city, stage, error, source_url=None, source_kind=None, scraper=None, context=None):
    entry = {
        "timestamp": datetime.datetime.now(est_timezone).isoformat(),
        "city": city,
        "stage": stage,
        "error": str(error),
    }
    if source_url:
        entry["source_url"] = source_url
    if source_kind:
        entry["source_kind"] = source_kind
    if scraper:
        entry["scraper"] = scraper
    if context:
        entry["context"] = context
    if isinstance(error, BaseException):
        entry["error_type"] = type(error).__name__
        entry["traceback"] = traceback.format_exc()
    return entry


def fetch_events_from_source(source, city):
    source_url = source.get("url", "")
    source_kind = infer_source_kind(source_url)
    unmatched_sources = []
    error_entries = []

    try:
        if source_kind == "meetup":
            print(f"Fetching events from {source_url}")
            upcoming_page_content = scrape_meetup.fetch_meetup_page(source_url)
            meetup_token = sanitize_event_name(source_url, max_length=48)
            meetup_cache_path = os.path.join(city, f"meetup_upcoming_{meetup_token}.html")
            with open(meetup_cache_path, "w+", encoding="utf-8") as f:
                f.write(upcoming_page_content)

            upcoming_next_data = scrape_meetup.extract_next_data(upcoming_page_content)
            events = scrape_meetup.parse_meetup_events(
                upcoming_next_data,
                include_past=False,
                source_url=source_url,
            )
            return apply_source_metadata(events, source), unmatched_sources, error_entries

        if source_kind == "eventbrite_event":
            print(f"Fetching events from {source_url}")
            return apply_source_metadata(
                scrape_eventbrite.parse_eventbrite_event(source_url),
                source,
            ), unmatched_sources, error_entries

        if source_kind == "eventbrite_org":
            print(f"Fetching org events from {source_url}")
            return apply_source_metadata(
                scrape_eventbrite_org.scrape_eventbrite_organizer(source_url),
                source,
            ), unmatched_sources, error_entries

        if source_kind == "jotform":
            print(f"Fetching events from {source_url}")
            return apply_source_metadata(
                scrape_jotform.parse_jotform_event(source_url),
                source,
            ), unmatched_sources, error_entries

        if source_kind == "luma_event":
            print(f"Fetching events from {source_url}")
            return apply_source_metadata(
                scrape_luma.parse_luma_event_page(source_url),
                source,
            ), unmatched_sources, error_entries

        if source_kind == "luma_user":
            user_api_id = extract_luma_user_id(source)
            if not user_api_id:
                unmatched_sources.append(
                    {
                        **source_pattern_details(source),
                        "reason": "missing_luma_user_api_id",
                    }
                )
                return [], unmatched_sources, error_entries
            print(f"Fetching events from {source_url}")
            return apply_source_metadata(
                scrape_luma_user.fetch_and_convert_luma_events(user_api_id),
                source,
            ), unmatched_sources, error_entries

        if source_kind == "luma_org":
            print(f"Fetching events from {source_url}")
            return apply_source_metadata(
                scrape_luma_orgpage.fetch_and_parse_luma_events(source_url),
                source,
            ), unmatched_sources, error_entries

        if source_kind == "luma_calendar":
            print(f"Fetching events from {source_url}")
            return apply_source_metadata(
                scrape_luma_calendar.scrape(source_url),
                source,
            ), unmatched_sources, error_entries

        if source_kind == "google_form":
            print(f"Fetching events from {source_url}")
            return apply_source_metadata(scrape_gform.scrape(source_url), source), unmatched_sources, error_entries

        if source_kind == "gdg":
            chapter_id = extract_gdg_chapter_id(source)
            if chapter_id is None:
                unmatched_sources.append(
                    {
                        **source_pattern_details(source),
                        "reason": "missing_gdg_chapter_id",
                    }
                )
                return [], unmatched_sources, error_entries
            print(f"Fetching GDG Chapter {chapter_id}")
            return apply_source_metadata(scrape_gdg.scrapeChapterID(chapter_id), source), unmatched_sources, error_entries

        unmatched_sources.append(
            {
                **source_pattern_details(source),
                "reason": "unknown_source_pattern",
            }
        )
        return [], unmatched_sources, error_entries

    except Exception as e:
        print(e)
        error_entries.append(
            build_error_entry(
                city=city,
                stage="source_fetch",
                error=e,
                source_url=source_url,
                source_kind=source_kind or "unknown",
            )
        )
        return [], unmatched_sources, error_entries


def fetch_all_sources(sources, city, max_workers=6):
    if not sources:
        return [], [], []

    new_events = []
    unmatched_sources = []
    scrape_errors = []

    grouped_sources = {}
    for index, source in enumerate(sources):
        source_kind = infer_source_kind(source.get("url", "")) or "unknown"
        grouped_sources.setdefault(source_kind, []).append((index, source))

    ordered_results = []
    futures = {}
    executors = []

    try:
        for source_kind, grouped_entries in grouped_sources.items():
            kind_limit = SOURCE_KIND_CONCURRENCY.get(source_kind, SOURCE_KIND_CONCURRENCY["unknown"])
            worker_count = max(1, min(kind_limit, max_workers, len(grouped_entries)))
            executor = ThreadPoolExecutor(max_workers=worker_count)
            executors.append(executor)

            for index, source in grouped_entries:
                future = executor.submit(fetch_events_from_source, source, city)
                futures[future] = index

        for future in as_completed(futures):
            index = futures[future]
            events, unmatched, errors = future.result()
            ordered_results.append((index, events, unmatched, errors))
    finally:
        for executor in executors:
            executor.shutdown(wait=True)

    for _, events, unmatched, errors in sorted(ordered_results, key=lambda item: item[0]):
        new_events.extend(events)
        unmatched_sources.extend(unmatched)
        scrape_errors.extend(errors)

    return new_events, unmatched_sources, scrape_errors


def parse_markdown_to_html(text):
    """Convert markdown text to HTML for ICS description"""
    if not text:
        return ""
    # Replace markdown links with HTML links first (markdown module doesn't handle this well)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    html = markdown.markdown(text)
    return html


def extract_text_from_html(html_text):
    """Use BeautifulSoup to extract clean text from HTML"""
    if not html_text:
        return ""

    try:
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")

        # Handle lists specially to preserve structure
        for ul in soup.find_all(["ul", "ol"]):
            for li in ul.find_all("li"):
                # Add bullet point to list items
                li.string = f"• {li.get_text(strip=True)}"
            # Replace the list with line breaks between items
            ul.replace_with(
                "\n".join([li.get_text(strip=True) for li in ul.find_all("li")])
            )

        # Handle line breaks and paragraphs
        for br in soup.find_all("br"):
            br.replace_with("\n")

        for p in soup.find_all("p"):
            p.append("\n")

        # Handle headers
        for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            header_text = header.get_text(strip=True)
            if header_text:
                header.replace_with(f"\n{header_text}\n")

        # Extract clean text
        clean_text = soup.get_text()

        # Clean up whitespace
        clean_text = re.sub(
            r"\n\s*\n", "\n\n", clean_text
        )  # Multiple newlines to double newline
        clean_text = re.sub(
            r"[ \t]+", " ", clean_text
        )  # Multiple spaces to single space
        clean_text = clean_text.strip()

        return clean_text

    except Exception as e:
        print(f"Error parsing HTML with BeautifulSoup: {e}")
        # Fallback to simple regex if BeautifulSoup fails
        return strip_html_tags_regex(html_text)


def strip_html_tags_regex(text):
    """Fallback regex-based HTML tag removal"""
    if not text:
        return ""

    # Remove HTML tags
    clean_text = re.sub("<.*?>", "", text)

    # Convert common HTML entities
    clean_text = clean_text.replace("&amp;", "&")
    clean_text = clean_text.replace("&lt;", "<")
    clean_text = clean_text.replace("&gt;", ">")
    clean_text = clean_text.replace("&quot;", '"')
    clean_text = clean_text.replace("&#39;", "'")
    clean_text = clean_text.replace("&nbsp;", " ")

    # Remove escaped characters that aren't needed in descriptions
    clean_text = clean_text.replace("\\,", ",")
    clean_text = clean_text.replace("\\;", ";")

    # Clean up markdown remnants
    clean_text = re.sub(
        r"\\#\\#\\#\s*", "", clean_text
    )  # Remove escaped markdown headers
    clean_text = re.sub(r"#+\s*", "", clean_text)  # Remove remaining markdown headers

    # Clean up extra whitespace and newlines
    clean_text = re.sub(
        r"\n\s*\n", "\n\n", clean_text
    )  # Replace multiple newlines with double newline
    clean_text = re.sub(
        r"[ \t]+", " ", clean_text
    )  # Replace multiple spaces/tabs with single space
    clean_text = clean_text.strip()

    return clean_text


def parse_markdown_to_plain_text(markdown_text):
    """Convert markdown to plain text (removing markdown syntax)"""
    if not markdown_text:
        return ""

    # Remove markdown formatting
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", markdown_text)  # Bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # Italic
    text = re.sub(r"`(.*?)`", r"\1", text)  # Code
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # Links
    text = re.sub(r"^#+\s*(.*)$", r"\1", text, flags=re.MULTILINE)  # Headers
    text = re.sub(
        r"^[\*\-\+]\s*(.*)$", r"• \1", text, flags=re.MULTILINE
    )  # Bullet points
    text = re.sub(r"^\d+\.\s*(.*)$", r"\1", text, flags=re.MULTILINE)  # Numbered lists

    return text.strip()


def sanitize_event_name(name, max_length=80):
    """Return an ASCII-only, safe name for storing event assets."""
    if not name:
        name = "event"

    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_")

    if not sanitized:
        sanitized = "event"

    return sanitized[:max_length]


def events_to_ics(events_json, city, output_file="baltimore_tech_events.ics"):
    """
    Convert event JSON data to ICS format and save to a file using icalendar library
    
    Args:
        events_json (str or list): JSON string or list of event dictionaries
        output_file (str): Path to save the ICS file
    """
    # Try to import icalendar
    try:
        from icalendar import Calendar, Event as ICalEvent
        icalendar_available = True
    except ImportError:
        print("ERROR: icalendar library not available. Cannot generate ICS file.")
        print("Please install icalendar: pip install icalendar")
        return None
    
    # Parse JSON if it's a string
    if isinstance(events_json, str):
        events = json.loads(events_json)
    else:
        events = events_json

    # Create a new calendar
    cal = Calendar()
    cal.add('prodid', f'-//{city} Tech Events//CodeCollective//')
    cal.add('version', '2.0')
    cal.add('method', 'PUBLISH')

    event_count = 0
    
    # Add each event to the calendar
    for event_data in events:
        # Create event
        event = ICalEvent()
        
        # Set basic event properties
        event.add('summary', event_data.get("name", "Unnamed Event"))
        event.add('uid', f"{event_data.get('id', '')}-{datetime.datetime.now().timestamp()}@codecollective")
        event.add('dtstamp', datetime.datetime.now(datetime.timezone.utc))
        
        # Process description
        description = event_data.get("description", "")
        
        # First extract clean text from HTML using BeautifulSoup
        clean_description = extract_text_from_html(description)
        
        # Then parse any remaining markdown
        plain_description = parse_markdown_to_plain_text(clean_description)
        plain_description = plain_description[:200]
        
        # Add location and URL information to description
        location_info = event_data.get("location", {})
        location_str = ""
        if location_info:
            location_parts = [
                location_info.get("name", ""),
                location_info.get("address", ""),
                f"{location_info.get('city', '')}, {location_info.get('state', '')} {location_info.get('country', '')}",
            ]
            location_str = ", ".join(
                [p for p in location_parts if p and p.strip() and p.strip() != ", "]
            )
        
        # Add group name if available
        group_name = event_data.get("group", "")
        group_info = f"\n\nGroup: {group_name}" if group_name else ""
        
        # Add event URL if available
        event_url = event_data.get("url", "")
        url_info = f"\n\nEvent Link: {event_url}" if event_url else ""
        
        # Combine all information for the description (plain text only)
        full_description = f"{plain_description}{group_info}{url_info}".strip()
        
        # Ensure description is not empty
        if not full_description:
            full_description = "No description available"
        
        event.add('description', full_description)
        
        # Set date/time information
        start_str = event_data.get("startDate")
        end_str = event_data.get("endTime")
        
        if start_str:
            # Parse ISO format dates
            try:
                start_time = parse(start_str)
                # Make timezone aware if needed
                if start_time.tzinfo is None:
                    start_time = est_timezone.localize(start_time)
                
                event.add('dtstart', start_time)
                
                if end_str:
                    end_time = parse(end_str)
                    if end_time.tzinfo is None:
                        end_time = est_timezone.localize(end_time)
                    event.add('dtend', end_time)
                else:
                    # Default to 2 hours if no end time specified
                    event.add('dtend', start_time + datetime.timedelta(hours=2))
                    
            except ValueError as e:
                print(f"Error parsing date for event {event_data.get('name', 'Unknown')}: {e}")
                print(f"Start date string: {start_str}")
                if end_str:
                    print(f"End date string: {end_str}")
                continue
        else:
            print(f"Warning: Event '{event_data.get('name', 'Unknown')}' has no start date, skipping...")
            continue
        
        # Set location
        if location_str:
            event.add('location', location_str)
        
        # Set URL
        if event_url:
            event.add('url', event_url)
        
        # Add to calendar
        cal.add_component(event)
        event_count += 1

    # Write the calendar to a file
    with open(output_file, "wb") as f:
        f.write(cal.to_ical())

    print(f"Calendar with {event_count} events saved to {output_file}")
    return output_file


import os
import requests


def extract_proper_extension(url):
    """Extract proper file extension from URL, handling complex URLs with query parameters"""
    # First get the part before any query parameters
    url_without_query = url.split("?")[0]

    # Look for common image extensions in the URL
    import re

    matches = re.search(
        r"\.(jpe?g|png|gif|webp|svg|bmp)$", url_without_query, re.IGNORECASE
    )
    if matches:
        return matches.group(1).lower()

    # If we can't find a standard extension, check if there's any extension
    path_parts = url_without_query.split(".")
    if len(path_parts) > 1:
        last_part = path_parts[-1]
        # Verify it's a reasonable length for an extension
        if len(last_part) <= 5:
            return last_part.lower()

    # Default fallback to jpg for Eventbrite images (which are typically JPEG)
    return "jpg"


from PIL import Image
from io import BytesIO


def download_image(url, filename):
    """Download image from URL and save to filename"""
    try:
        # Make sure the directory exists
        import os

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Download the image
        import requests

        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Save the image
        with open(filename, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return True
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return False


def build_geocode_query(location_data, default_city=""):
    """Construct a geocoding query from the location metadata."""
    if not location_data:
        return ""

    candidates = [
        location_data.get("address"),
        location_data.get("name"),
        location_data.get("city"),
        location_data.get("state"),
        location_data.get("postalCode"),
        location_data.get("country"),
    ]

    if default_city:
        candidates.append(default_city)

    cleaned = []
    seen = set()
    for value in candidates:
        if not value:
            continue
        trimmed = value.strip()
        lowered = trimmed.lower()
        if not trimmed:
            continue
        if lowered.startswith("http://") or lowered.startswith("https://"):
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(trimmed)

    return ", ".join(cleaned)


def geocode_upcoming_events(city, geocode_cache, events_path=None):
    """Geocode events stored in upcoming_events.json for the provided city."""
    events_path = events_path or os.path.join(city, "upcoming_events.json")
    if not os.path.exists(events_path):
        print(f"No upcoming_events.json found for {city}; skipping geocoding")
        return None, False

    try:
        with open(events_path, "r", encoding="utf-8") as f:
            events = json.load(f)
    except Exception as exc:
        print(f"Unable to read events file for {city}: {exc}")
        return None, False

    geolocator = Nominatim(user_agent="codecollective-calendar")
    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1,
        max_retries=2,
        error_wait_seconds=2.0,
        swallow_exceptions=True,
    )

    updated_events = 0
    cache_updated = False

    for event in events:
        location_data = event.get("location") or {}
        if not location_data:
            print(f"[geocode] Skipping '{event.get('name')}' – no location data present.")
            continue

        lat = location_data.get("latitude")
        lon = location_data.get("longitude")

        # Normalize the address used for caching lookups
        cache_key_source = (
            location_data.get("address")
            or location_data.get("name")
            or ""
        )
        cache_key = normalize_address(cache_key_source) if cache_key_source else ""

        if lat and lon:
            try:
                lat_val = float(lat)
                lon_val = float(lon)
            except (TypeError, ValueError):
                print(f"[geocode] '{event.get('name')}' has invalid latitude/longitude values; skipping cache update.")
                continue

            if cache_key:
                cached = geocode_cache.get(cache_key)
                if not cached or cached.get("latitude") != lat_val or cached.get("longitude") != lon_val:
                    geocode_cache[cache_key] = {"latitude": lat_val, "longitude": lon_val}
                    cache_updated = True
            print(f"[geocode] '{event.get('name')}' already has coordinates; updating cache if needed.")
            continue

        query = build_geocode_query(location_data, city)
        if not query:
            print(f"[geocode] Skipping '{event.get('name')}' – could not build geocode query from location data.")
            continue

        coords = None
        if cache_key and cache_key in geocode_cache:
            print(f"[geocode] Using cached coordinates for '{event.get('name')}'.")
            coords = geocode_cache[cache_key]
        else:
            try:
                print(f"[geocode] Querying geocoder for '{event.get('name')}': {query}")
                result = geocode(query)
            except Exception as exc:
                print(f"[geocode] Geocoding failed for '{query}': {exc}")
                continue
            if result:
                coords = {"latitude": result.latitude, "longitude": result.longitude}
            else:
                print(f"[geocode] No geocode result returned for '{query}'.")

        if not coords:
            print(f"[geocode] Skipping '{event.get('name')}' – no coordinates available.")
            continue

        try:
            location_data["latitude"] = float(coords["latitude"])
            location_data["longitude"] = float(coords["longitude"])
        except (TypeError, ValueError, KeyError):
            continue

        event["location"] = location_data
        updated_events += 1

        if cache_key:
            geocode_cache[cache_key] = {
                "latitude": location_data["latitude"],
                "longitude": location_data["longitude"],
            }
            cache_updated = True

    if updated_events:
        with open(events_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4)
        print(f"Geocoded {updated_events} event(s) for {city}.")
    else:
        print(f"No new geocoding data added for {city}.")

    return events, cache_updated


def main(city = "baltimore"):
    newEvents = []
    cache_path = os.path.join(city, "geocode_cache.json")
    geocode_cache = load_geocode_cache(cache_path)
    cache_updated = False

    module = importlib.import_module(f"{city}.event_sources")
    sources = flatten_sources(module.sources)
    source_events, unmatched_sources, scrape_errors = fetch_all_sources(sources, city)
    newEvents += source_events

    unmatched_sources_path = os.path.join(city, "unmatched_source_patterns.json")
    with open(unmatched_sources_path, "w+", encoding="utf-8") as f:
        json.dump(unmatched_sources, f, indent=4)
    if unmatched_sources:
        print(f"Unmatched source patterns saved to {unmatched_sources_path}")

    def error_logger(stage, error, source_url=None, source_kind=None, scraper=None, context=None):
        entry = build_error_entry(
            city=city,
            stage=stage,
            error=error,
            source_url=source_url,
            source_kind=source_kind,
            scraper=scraper,
            context=context,
        )
        scrape_errors.append(entry)
        return entry


    # upcoming_events += scrape_equitech.scrape_equitech_tuesday()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    if city == "dc":
        dc_gen_calendar = importlib.import_module("dc.gen_calendar")
        newEvents += dc_gen_calendar.collect_events(city, error_logger=error_logger)
        
    if city == "baltimore":
        baltimore_gen_calendar = importlib.import_module("baltimore.gen_calendar")
        newEvents += baltimore_gen_calendar.collect_events(city, error_logger=error_logger)

    if city == "westvirginia":

        newEvents += scrape_ics.fetch_calendar_events(
            ICS_URL="https://wvbusinesslink.com/?post_type=tribe_events&ical=1&eventDisplay=list",
            imageURL="https://baltimoreindiegames.com/wp-content/uploads/2025/03/BIG_small.png",
            eventUrl="https://baltimoreindiegames.com/events/",
            city="westvirginia",
            preface="",
            recurring=False
        )

    if city == "virtual":
        try:
            scrape_abwippm = importlib.import_module("virtual.scrape_ABWIPPM")
            newEvents += scrape_abwippm.scrape_events()
        except Exception as e:
            print(f"Error fetching ABWIPPM events: {e}")
            error_logger("city_collect", e, scraper="virtual.scrape_ABWIPPM")

    invalid_events = []

    # Convert all datetime strings in newEvents to timezone-aware datetime objects
    for event in newEvents:
        if "startDate" in event:
            try:
                start_dt = parse(event["startDate"])
                if start_dt.tzinfo is None:
                    start_dt = est_timezone.localize(start_dt)
                event["startDate"] = start_dt.isoformat()
            except Exception as e:
                print(f"Error converting datetime for event {event.get('name', 'Unknown')}: {e}")
                error_logger("normalize_datetime", e, context={"event_name": event.get("name", "Unknown")})

    # Download images for each event
    for event in newEvents:
        # Download images if available
        if "imageUrl" in event and event["imageUrl"]:
            image_url = event["imageUrl"]

            safe_event_name = sanitize_event_name(event.get("name"))
            image_filename = f"event_images/{safe_event_name}.webp"

            # Update event data with local path
            event["imageUrl"] = "/" + image_filename

            if os.path.exists(image_filename):
                # print(f"Image already exists: {image_filename}, skipping download.")
                continue

            try:
                response = requests.get(image_url, headers=headers, timeout=10)
                response.raise_for_status()

                # Load image
                img = Image.open(BytesIO(response.content))

                # Resize while keeping aspect ratio
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)

                # Save as WebP with high compression
                img.save(image_filename, "WEBP", quality=80, method=6)

                print(f"Saved image: {image_filename}")

            except Exception as e:
                print(f"Failed to process image for event {event['name']}: {e}")
                error_logger(
                    "image_download",
                    e,
                    source_url=image_url,
                    context={"event_name": event.get("name", "Unknown")},
                )
                # revert url
                event["imageUrl"] = image_url

    nonerror_newevents = []
    time_now = datetime.datetime.now(est_timezone)
    today_date = time_now.date()

    for event in newEvents:
        startDate = event.get("startDate")
        if not startDate:
            print(f'{event.get("name")} missing startdate ')
            event["invalid_reason"] = 'missing startdate'
            invalid_events += [event]
            continue

        startDateTime = parse(event["startDate"])
        # Make startDateTime timezone-aware if it's naive
        if startDateTime.tzinfo is None:
            startDateTime = est_timezone.localize(startDateTime)

        if (
            startDateTime.date() == datetime.date(2025, 6, 28)
            and "unity" not in event.get("name", "").lower()
        ):
            print(f"Skipping event on June 28, 2025: {event['name']}")
            event["invalid_reason"] = 'UNITY CONFLICT'
            invalid_events += [event]
            continue

        if startDateTime.date() >= today_date:
            nonerror_newevents += [event]
        else:
            event["invalid_reason"] = 'Already happened'
            invalid_events += [event]
            print(f'{event.get("name")} already happened ')

        if "Casual Coding" in event.get("name", ""):
            event["recurring"] = True

    def get_event_signature_strict(event):
        e2 = event.copy()
        del e2["scrapeTime"]
        return json.dumps(e2, sort_keys=True)

    def get_event_signature(event):
        """Creates a unique signature for duplicate detection"""
        name = event.get("name", "").strip().lower()
        start = str(parse(event.get("startDate", "")).date())
        url = event.get("url", "").split("?")[0].lower()  # Remove query params
        location = str(event.get("location", {}).get("name", "")).strip().lower()
        return f"{name[:10]}||{start}"

    unique_events = []
    date_occupied = set()  # Track which dates already have events
    unique_event_signatures = set()  # Track all unique event signatures

    # --- PHASE 0: mix with existing events
    # read existing events from file
    with open(os.path.join(city, "manual_events.json"), "r") as f:
        existing_events_in_file = json.loads(f.read())
    upcoming_existing_events_in_file = []
    for event in existing_events_in_file:
        startDateTime = parse(event["startDate"])
        # Make startDateTime timezone-aware if it's naive
        if startDateTime.tzinfo is None:
            startDateTime = est_timezone.localize(startDateTime)
        if startDateTime.date() >= today_date:
            upcoming_existing_events_in_file += [event]

    existing_sigs = [get_event_signature(e) for e in upcoming_existing_events_in_file]
    total_events = []
    for event in nonerror_newevents:
        sig = get_event_signature(event)
        if sig not in existing_sigs:
            total_events += [event]

    total_events += upcoming_existing_events_in_file
    cache_updated = apply_geocode_cache(total_events, geocode_cache) or cache_updated
    # --- PHASE 1: Process NON-RECURRING events first ---
    for event in total_events:
        # Skip recurring events in first pass
        if event.get("recurring"):
            continue

        # Ensure scrapeTime exists
        if not event.get("scrapeTime"):
            event["scrapeTime"] = str(datetime.datetime.now())

        # Parse date
        try:
            event_date = parse(event.get("startDate", "")).date()
        except:
            event["invalid_reason"] = "Bad startdate"
            invalid_events += [event]
            continue  # Skip if invalid date

        event_sig = get_event_signature(event)

        # Check if this is a duplicate
        if event_sig in unique_event_signatures:
            # Find the existing event with this signature
            existing_event = next(
                (e for e in unique_events if get_event_signature(e) == event_sig), None
            )
            if existing_event:
                # Only update if the content has actually changed
                if get_event_signature_strict(
                    existing_event
                ) != get_event_signature_strict(event):
                    # Content changed - replace the event
                    existing_event["invalid_reason"] = "Replaced by more recent event"
                    invalid_events += [existing_event]
                    unique_events.remove(existing_event)
                    unique_events.append(event)
            else:
                event["invalid_reason"] = "Already exists with same signature and earlier scrapedate"
                invalid_events += [event]
            continue

        # If not a duplicate, add it
        unique_events.append(event)
        unique_event_signatures.add(event_sig)
        date_occupied.add(event_date)  # Mark this date as occupied

    # --- PHASE 2: Process RECURRING events ---
    # Create set of signatures from UNIQUE events (not original list)
    unique_event_signatures = {get_event_signature(e) for e in unique_events}

    for event in total_events:
        # Only process recurring events in second pass
        if not event.get("recurring"):
            continue

        if "Member Meeting" in event.get("name"):
            event["invalid_reason"] = "Member meeting"
            invalid_events += [event]
            continue

        event_name = event.get("name", "").strip().lower()
        event_start = event.get("startDate", "")

        # Ensure scrapeTime exists
        if not event.get("scrapeTime"):
            event["scrapeTime"] = str(datetime.datetime.now())

        # Parse date
        try:
            event_date = parse(event_start).date()
        except:
            event["invalid_reason"] = "Invalid date"
            invalid_events += [event]
            continue  # Skip if invalid date

        event_sig = get_event_signature(event)

        # Only add if:
        # 1. No other event exists on this date (strict), AND
        # 2. This isn't a duplicate of any existing event
        if event_date not in date_occupied and event_sig not in unique_event_signatures:
            unique_events.append(event)
            unique_event_signatures.add(event_sig)  # Keep this in sync
        else:
            event["invalid_reason"] = "Recurring event removed when non-recurring event is present"
            invalid_events += [event]
        #    print(f"Added recurring event: {event_name} on {event_date}")
        # else:
        #    print(f"Skipping recurring event: {event_name} (conflict on {event_date})")

    # Sort all events by date
    unique_events.sort(key=lambda x: est_timezone.localize(parse(x["startDate"])) if parse(x["startDate"]).tzinfo is None else parse(x["startDate"]))
    # Sort events by startDate
    sorted_events = sorted(
        (e for e in unique_events if "startDate" in e),
        key=lambda e: est_timezone.localize(parse(e["startDate"])) if parse(e["startDate"]).tzinfo is None else parse(e["startDate"]),
    )

    # add the categories
    for event in sorted_events:
        # find earliest match, then break
        inferred_tags = []
        for url2tag in tag_rules.tag_rules_url:
            urlpart, tag_list = url2tag
            if urlpart in event.get("url", ""):
                inferred_tags = tag_list
                break
        event["tags"] = merge_tags(event.get("tags"), inferred_tags)

    # Save upcoming events to a file
    with open(os.path.join(city, "upcoming_events.json"), "w+", encoding="utf-8") as f:
        json.dump(sorted_events, f, indent=4)
        print(f"Upcoming events saved to upcoming_events.json")

    GEOCODE = False
    if GEOCODE:
        geocoded_payload, geocode_cache_changed = geocode_upcoming_events(city, geocode_cache)
        if geocoded_payload is not None:
            sorted_events = geocoded_payload
        cache_updated = cache_updated or geocode_cache_changed

    # Save upcoming events to a file
    with open(os.path.join(city, "skipped_events.json"), "w+", encoding="utf-8") as f:
        json.dump(invalid_events, f, indent=4)
        print(f"Upcoming events saved to skipped_events.json")

    scrape_errors_path = os.path.join(city, "scrape_errors.json")
    with open(scrape_errors_path, "w+", encoding="utf-8") as f:
        json.dump(scrape_errors, f, indent=4)
    if scrape_errors:
        print(f"Scrape errors saved to {scrape_errors_path}")

    events_to_ics(sorted_events, city, output_file=os.path.join(city, "cc_events.ics"))
    os.system("cp baltimore/cc_events.ics .")
    os.system("cp baltimore/upcoming_events.json .")
    if GEOCODE:
        generate_events_map_page(city)
        if cache_updated:
            save_geocode_cache(geocode_cache, cache_path)
    genSimpleCalendar.main(city)

if __name__ == "__main__":
    cities = ["baltimore", "westvirginia", "hawaii", "dc", "pittsburgh", "virtual"]
    if len(sys.argv) > 1:
        cities = sys.argv[1:]
    for city in cities:
        main(city)
