import scrape_meetup
import scrape_eventbrite
import scrape_jotform
import scrape_spark
import scrape_gbc
import scrape_luma
import scrape_ics
import scrape_starTUp
import scrape_jhuapl
import scrape_big
import scrape_gform
import scrape_luma_orgpage
import scrape_luma_user
import scrape_bwtech
import json
from ics import Calendar, Event
import datetime
import pytz
from bs4 import BeautifulSoup
import re
import scrape_eventbrite_org
import markdown
from dateutil.parser import parse
import sys
import genSimpleCalendar

# Define the timezone for EST
est_timezone = pytz.timezone("America/New_York")


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


def events_to_ics(events_json, city, output_file="baltimore_tech_events.ics"):
    """
    Convert event JSON data to ICS format and save to a file

    Args:
        events_json (str or list): JSON string or list of event dictionaries
        output_file (str): Path to save the ICS file
    """
    # Parse JSON if it's a string
    if isinstance(events_json, str):
        events = json.loads(events_json)
    else:
        events = events_json

    # Create a new calendar
    cal = Calendar()
    cal.creator = f"{city} Tech Events"

    # Add each event to the calendar
    for event_data in events:
        event = Event()

        # Set basic event properties
        event.name = event_data.get("name", "Unnamed Event")
        event.created = datetime.datetime.now(datetime.timezone.utc)

        # Process description - use BeautifulSoup for HTML extraction
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

        event.description = full_description

        # Set date/time information
        start_str = event_data.get("startDate")
        end_str = event_data.get("endTime")

        if start_str:
            # Parse ISO format dates
            try:
                start_time = parse(start_str)
                event.begin = start_time

                if end_str:
                    end_time = parse(end_str)
                    event.end = end_time
                else:
                    # Default to 2 hours if no end time specified
                    event.end = start_time + datetime.timedelta(hours=2)

            except ValueError as e:
                print(f"Error parsing date for event {event.name}: {e}")
                print(f"Start date string: {start_str}")
                if end_str:
                    print(f"End date string: {end_str}")
                continue
        else:
            print(f"Warning: Event '{event.name}' has no start date, skipping...")
            continue

        # Set location
        if location_str:
            event.location = location_str

        # Set URL
        if event_url:
            event.url = event_url

        # Add to calendar
        cal.events.add(event)

    # Write the calendar to a file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(str(cal))

    print(f"Calendar with {len(cal.events)} events saved to {output_file}")
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


def main(city = "baltimore"):
    newEvents = []

    import importlib

    module = importlib.import_module(f"{city}.event_sources")
    sources = module.sources

    # Loop through each meetup URL
    for MEETUP_URL in sources.get("Meetup", []):
        print(f"Fetching events from {MEETUP_URL}")
        # Fetch upcoming events
        upcoming_page_content = scrape_meetup.fetch_meetup_page(MEETUP_URL)
        with open(os.path.join(city, "meetup_upcoming.html"), "w+", encoding="utf-8") as f:
            f.write(upcoming_page_content)

        # Extract the __NEXT_DATA__ JSON for upcoming events
        upcoming_next_data = scrape_meetup.extract_next_data(upcoming_page_content)

        # Parse upcoming events
        newEvents += scrape_meetup.parse_meetup_events(
            upcoming_next_data, include_past=True
        )

    for EVENTBRITE_URL in sources.get("Eventbrite", []):
        try:
            print(f"Fetching events from {EVENTBRITE_URL}")
            newEvents += scrape_eventbrite.parse_eventbrite_event(EVENTBRITE_URL)
        except Exception as e:
            print(e)

    for EVENTBRITE_URL in sources.get("Eventbrite Orgs", []):
        try:
            print(f"Fetching org events from {EVENTBRITE_URL}")
            newEvents += scrape_eventbrite_org.scrape_eventbrite_organizer(
                EVENTBRITE_URL
            )
        except Exception as e:
            print(e)

    for JOTFORM_URL in sources.get("Jotform", []):
        print(f"Fetching events from {JOTFORM_URL}")
        newEvents += [scrape_jotform.parse_jotform_event(JOTFORM_URL)]

    for LUMA_URL in sources.get("Luma", []):
        print(f"Fetching events from {LUMA_URL}")
        newEvents += [scrape_luma.parse_luma_event_page(LUMA_URL)]

    for LUMA_URL in sources.get("Luma Users", []):
        print(f"Fetching events from {LUMA_URL}")
        newEvents += scrape_luma_user.fetch_and_convert_luma_events(LUMA_URL)

    for LUMA_URL in sources.get("Luma Orgs", []):
        print(f"Fetching events from {LUMA_URL}")
        try:
            newEvents += scrape_luma_orgpage.fetch_and_parse_luma_events(LUMA_URL)
        except Exception as e:
            print(f"Error fetching Luma events from {LUMA_URL}: {e}")


    for URL in sources.get("Google Forms", []):
        print(f"Fetching events from {URL}")
        try:
            newEvents += scrape_gform.scrape(URL)
        except Exception as e:
            print(f"Error fetching calendar events: {e}")


    # upcoming_events += scrape_equitech.scrape_equitech_tuesday()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    if city == "baltimore":

        gbc_events = scrape_gbc.scrape_gbc_events()
        newEvents += gbc_events
        try:
            newEvents += scrape_ics.fetch_calendar_events(
                ICS_URL="http://www.google.com/calendar/ical/baltimorenode.org_5jbobahkshgj11vut3cndhppoo%40group.calendar.google.com/public/basic.ics",
                imageURL="https://www.baltimorenode.org/wp-content/uploads/2013/11/node-logo.png",
                city=city,
                eventUrl="https://baltimorenode.org/events/",
                preface="Node ",
            )
        except Exception as e:
            print(f"Error fetching calendar events: {e}")

        try:
            newEvents += scrape_ics.fetch_calendar_events(
                ICS_URL="https://calendar.google.com/calendar/ical/unallocatedspacehq@gmail.com/public/basic.ics",
                imageURL="https://www.unallocatedspace.org/wp-content/uploads/2017/03/UnallocatedLogoSmall.png",
                city=city,
                eventUrl="https://www.unallocatedspace.org/events/",
                preface="UAS ",
            )
        except Exception as e:
            print(f"Error fetching calendar events: {e}")

        try:
            newEvents += scrape_ics.processICS(
                CACHE_FILENAME="maryland-stem-festival-96ecc18ef7d.ics",
                imageURL="https://marylandstemfestival.org/wp-content/uploads/2024/06/Family-Feud-group-Pix-1-scaled-e1717876361661.jpeg",
                eventUrl="https://marylandstemfestival.org/events/month/",
                preface="STEMFest ",
            )
        except Exception as e:
            print(f"Error fetching calendar events: {e}")

        try:
            newEvents += scrape_ics.fetch_calendar_events(
                ICS_URL="https://baltimoreindiegames.com/events/list/?ical=1",
                city=city,
                imageURL="https://baltimoreindiegames.com/wp-content/uploads/2025/03/BIG_small.png",
                eventUrl="https://baltimoreindiegames.com/events/",
                recurring=False,
                preface="",
            )
        except Exception as e:
            print(f"Error fetching calendar events: {e}")

        try:
            newEvents += scrape_spark.scrape_spark_events()
        except Exception as e:
            print(f"Error fetching calendar events: {e}")

        try:
            newEvents += scrape_bwtech.scrape_events()
        except Exception as e:
            print(f"Error fetching calendar events: {e}")

        try:
            newEvents += scrape_starTUp.scrape_towson_events()
        except Exception as e:
            print(f"Error fetching calendar events: {e}")

        # JHUAPL excluded because of too many events external to Baltimore tech scene
        #try:
        #    newEvents += scrape_jhuapl.scrape_jhu_events()
        #except Exception as e:
        #    print(f"Error fetching calendar events: {e}")

        try:
            newEvents += scrape_big.main()
        except Exception as e:
            print(f"Error fetching calendar events: {e}")

    if city == "westvirginia":

        newEvents += scrape_ics.fetch_calendar_events(
            ICS_URL="https://wvbusinesslink.com/?post_type=tribe_events&ical=1&eventDisplay=list",
            imageURL="https://baltimoreindiegames.com/wp-content/uploads/2025/03/BIG_small.png",
            eventUrl="https://baltimoreindiegames.com/events/",
            city="westvirginia",
            preface="",
            recurring=False
        )
    invalid_events = []

    # Download images for each event
    for event in newEvents:
        # Download images if available
        if "imageUrl" in event and event["imageUrl"]:
            image_url = event["imageUrl"]

            # Create a valid filename with all spaces replaced by underscores
            safe_event_name = (
                event["name"]
                .replace(" ", "_")
                .replace("/", "_")
                .replace("\\", "_")
                .replace("'", "_")
                .replace(":", "_")
                .replace("(", "_")
                .replace(")", "_")
                .replace("#", "_")
            )
            image_filename = f"event_images/{safe_event_name}.webp"

            # Update event data with local path
            event["imageUrl"] = "/" + image_filename

            if os.path.exists(image_filename):
                # print(f"Image already exists: {image_filename}, skipping download.")
                continue

            try:
                extension = extract_proper_extension(image_url)

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
                # revert url
                event["imageUrl"] = image_url

    nonerror_newevents = []
    time_now = datetime.datetime.now(est_timezone)

    for event in newEvents:
        startDate = event.get("startDate")
        if not startDate:
            print(f'{event.get("name")} missing startdate ')
            event["invalid_reason"] = 'missing startdate'
            invalid_events += [event]
            continue

        startDateTime = parse(event["startDate"])

        if (
            startDateTime.date() == datetime.date(2025, 6, 28)
            and "unity" not in event.get("name", "").lower()
        ):
            print(f"Skipping event on June 28, 2025: {event['name']}")
            event["invalid_reason"] = 'UNITY CONFLICT'
            invalid_events += [event]
            continue

        if startDateTime > time_now:
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
        if startDateTime > time_now:
            upcoming_existing_events_in_file += [event]

    existing_sigs = [get_event_signature(e) for e in upcoming_existing_events_in_file]
    total_events = []
    for event in nonerror_newevents:
        sig = get_event_signature(event)
        if sig not in existing_sigs:
            total_events += [event]

    total_events += upcoming_existing_events_in_file
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
    unique_events.sort(key=lambda x: parse(x["startDate"]))
    # Sort events by startDate
    sorted_events = sorted(
        (e for e in unique_events if "startDate" in e),
        key=lambda e: parse(e["startDate"]),
    )

    # Save upcoming events to a file
    with open(os.path.join(city, "upcoming_events.json"), "w+", encoding="utf-8") as f:
        json.dump(sorted_events, f, indent=4)
        print(f"Upcoming events saved to upcoming_events.json")

    # Save upcoming events to a file
    with open(os.path.join(city, "skipped_events.json"), "w+", encoding="utf-8") as f:
        json.dump(invalid_events, f, indent=4)
        print(f"Upcoming events saved to skipped_events.json")

    events_to_ics(sorted_events, city, output_file=os.path.join(city, "cc_events.ics"))
    os.system("cp baltimore/cc_events.ics .")
    os.system("cp baltimore/upcoming_events.json .")
    genSimpleCalendar.main(city)

if __name__ == "__main__":
    cities = ["baltimore", "westvirginia"]
    if len(sys.argv) > 1:
        cities = sys.argv[1:]
    for city in cities:
        main(city)