import scrape_meetup
import scrape_eventbrite
import scrape_jotform
import scrape_spark
import scrape_gbc
import scrape_luma
import scrape_ics
import scrape_starTUp
import json
from ics import Calendar, Event
import datetime
import pytz
from bs4 import BeautifulSoup
import re
import scrape_luma_orgpage
import scrape_eventbrite_org
import markdown
from dateutil.parser import parse

# Define the timezone for EST
est_timezone = pytz.timezone("America/New_York")

def parse_markdown_to_html(text):
    """Convert markdown text to HTML for ICS description"""
    if not text:
        return ""
    # Replace markdown links with HTML links first (markdown module doesn't handle this well)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    html = markdown.markdown(text)
    return html

def extract_text_from_html(html_text):
    """Use BeautifulSoup to extract clean text from HTML"""
    if not html_text:
        return ""
    
    try:
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_text, 'html.parser')
        
        # Handle lists specially to preserve structure
        for ul in soup.find_all(['ul', 'ol']):
            for li in ul.find_all('li'):
                # Add bullet point to list items
                li.string = f"• {li.get_text(strip=True)}"
            # Replace the list with line breaks between items
            ul.replace_with('\n'.join([li.get_text(strip=True) for li in ul.find_all('li')]))
        
        # Handle line breaks and paragraphs
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        for p in soup.find_all('p'):
            p.append('\n')
        
        # Handle headers
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            header_text = header.get_text(strip=True)
            if header_text:
                header.replace_with(f"\n{header_text}\n")
        
        # Extract clean text
        clean_text = soup.get_text()
        
        # Clean up whitespace
        clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)  # Multiple newlines to double newline
        clean_text = re.sub(r'[ \t]+', ' ', clean_text)  # Multiple spaces to single space
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
    clean_text = re.sub('<.*?>', '', text)
    
    # Convert common HTML entities
    clean_text = clean_text.replace('&amp;', '&')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')
    clean_text = clean_text.replace('&quot;', '"')
    clean_text = clean_text.replace('&#39;', "'")
    clean_text = clean_text.replace('&nbsp;', ' ')
    
    # Remove escaped characters that aren't needed in descriptions
    clean_text = clean_text.replace('\\,', ',')
    clean_text = clean_text.replace('\\;', ';')
    
    # Clean up markdown remnants
    clean_text = re.sub(r'\\#\\#\\#\s*', '', clean_text)  # Remove escaped markdown headers
    clean_text = re.sub(r'#+\s*', '', clean_text)  # Remove remaining markdown headers
    
    # Clean up extra whitespace and newlines
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)  # Replace multiple newlines with double newline
    clean_text = re.sub(r'[ \t]+', ' ', clean_text)  # Replace multiple spaces/tabs with single space
    clean_text = clean_text.strip()
    
    return clean_text

def parse_markdown_to_plain_text(markdown_text):
    """Convert markdown to plain text (removing markdown syntax)"""
    if not markdown_text:
        return ""
    
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', markdown_text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)  # Italic
    text = re.sub(r'`(.*?)`', r'\1', text)  # Code
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
    text = re.sub(r'^#+\s*(.*)$', r'\1', text, flags=re.MULTILINE)  # Headers
    text = re.sub(r'^[\*\-\+]\s*(.*)$', r'• \1', text, flags=re.MULTILINE)  # Bullet points
    text = re.sub(r'^\d+\.\s*(.*)$', r'\1', text, flags=re.MULTILINE)  # Numbered lists
    
    return text.strip()

def events_to_ics(events_json, output_file="baltimore_tech_events.ics"):
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
    cal.creator = "Baltimore Tech Events Calendar Generator"
    
    # Add each event to the calendar
    for event_data in events:
        event = Event()
        
        # Set basic event properties
        event.name = event_data.get('name', 'Unnamed Event')
        event.created = datetime.datetime.now(datetime.timezone.utc)
        
        # Process description - use BeautifulSoup for HTML extraction
        description = event_data.get('description', '')
        
        # First extract clean text from HTML using BeautifulSoup
        clean_description = extract_text_from_html(description)
        
        # Then parse any remaining markdown
        plain_description = parse_markdown_to_plain_text(clean_description)
        plain_description = plain_description[:200]
        
        # Add location and URL information to description
        location_info = event_data.get('location', {})
        location_str = ""
        if location_info:
            location_parts = [
                location_info.get('name', ''),
                location_info.get('address', ''),
                f"{location_info.get('city', '')}, {location_info.get('state', '')} {location_info.get('country', '')}"
            ]
            location_str = ", ".join([p for p in location_parts if p and p.strip() and p.strip() != ', '])

        # Add group name if available
        group_name = event_data.get('group', '')
        group_info = f"\n\nGroup: {group_name}" if group_name else ""
        
        # Add event URL if available
        event_url = event_data.get('url', '')
        url_info = f"\n\nEvent Link: {event_url}" if event_url else ""
        
        # Combine all information for the description (plain text only)
        full_description = f"{plain_description}{group_info}{url_info}".strip()
        
        # Ensure description is not empty
        if not full_description:
            full_description = "No description available"
            
        event.description = full_description
        
        # Set date/time information
        start_str = event_data.get('startDate')
        end_str = event_data.get('endTime')
        
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
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(str(cal))
    
    print(f"Calendar with {len(cal.events)} events saved to {output_file}")
    return output_file

import os
import requests

def extract_proper_extension(url):
    """Extract proper file extension from URL, handling complex URLs with query parameters"""
    # First get the part before any query parameters
    url_without_query = url.split('?')[0]
    
    # Look for common image extensions in the URL
    import re
    matches = re.search(r'\.(jpe?g|png|gif|webp|svg|bmp)$', url_without_query, re.IGNORECASE)
    if matches:
        return matches.group(1).lower()
    
    # If we can't find a standard extension, check if there's any extension
    path_parts = url_without_query.split('.')
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
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                
        return True
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return False
    
from event_sources import sources

if __name__ == "__main__":
    # read existing events from file
    with open("./upcoming_events.json", "r") as f:
        upcoming_events = json.loads(f.read())

    # Loop through each meetup URL
    for MEETUP_URL in sources.get("Meetup", []):
        print(f"Fetching events from {MEETUP_URL}")
        # Fetch upcoming events
        upcoming_page_content = scrape_meetup.fetch_meetup_page(MEETUP_URL)
        with open("meetup_upcoming.html", "w+", encoding="utf-8") as f:
            f.write(upcoming_page_content)

        # Extract the __NEXT_DATA__ JSON for upcoming events
        upcoming_next_data = scrape_meetup.extract_next_data(upcoming_page_content)
        
        # Parse upcoming events
        upcoming_events += scrape_meetup.parse_meetup_events(upcoming_next_data, include_past=True)

    for EVENTBRITE_URL in sources.get("Eventbrite", []):
        try:
            print(f"Fetching events from {EVENTBRITE_URL}")
            upcoming_events += scrape_eventbrite.parse_eventbrite_event(EVENTBRITE_URL)
        except Exception as e:
            print(e)

    for EVENTBRITE_URL in sources.get("Eventbrite Orgs", []):
        try:
            print(f"Fetching org events from {EVENTBRITE_URL}")
            upcoming_events += scrape_eventbrite_org.scrape_eventbrite_organizer(EVENTBRITE_URL)
        except Exception as e:
            print(e)

    for JOTFORM_URL in sources.get("Jotform", []):
        print(f"Fetching events from {JOTFORM_URL}")
        upcoming_events += [scrape_jotform.parse_jotform_event(JOTFORM_URL)]

    for LUMA_URL in sources.get("Luma", []):
        print(f"Fetching events from {LUMA_URL}")
        upcoming_events += [scrape_luma.parse_luma_event_page(LUMA_URL)]

    for LUMA_URL in sources.get("Luma Orgs", []):
        print(f"Fetching events from {LUMA_URL}")
        try:
            upcoming_events += scrape_luma_orgpage.fetch_and_parse_luma_events(LUMA_URL)
        except Exception as e:
            print(f"Error fetching Luma events from {LUMA_URL}: {e}")

    gbc_events = scrape_gbc.scrape_gbc_events()
    upcoming_events += gbc_events
    
    #upcoming_events += scrape_equitech.scrape_equitech_tuesday()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        upcoming_events += scrape_ics.fetch_calendar_events(
            existing_events=upcoming_events,
            ICS_URL="https://calendar.google.com/calendar/ical/unallocatedspacehq@gmail.com/public/basic.ics")
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        upcoming_events += scrape_ics.fetch_calendar_events(
            existing_events=upcoming_events,
            ICS_URL='http://www.google.com/calendar/ical/baltimorenode.org_5jbobahkshgj11vut3cndhppoo%40group.calendar.google.com/public/basic.ics')
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        upcoming_events += scrape_ics.processICS(
            CACHE_FILENAME='maryland-stem-festival-96ecc18ef7d.ics',
            existing_events=upcoming_events,
            imageURL='https://marylandstemfestival.org/wp-content/uploads/2024/06/Family-Feud-group-Pix-1-scaled-e1717876361661.jpeg')
    except Exception as e:
        print(f"Error fetching calendar events: {e}")


    try:
        upcoming_events += scrape_spark.scrape_spark_events()
    except Exception as e:
        print(f"Error fetching calendar events: {e}")

    try:
        upcoming_events += scrape_starTUp.scrape_towson_events()
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        

    # Download images for each event
    for event in upcoming_events:
        # Download images if available
        if "imageUrl" in event and event["imageUrl"]:
            image_url = event["imageUrl"]

            # Create a valid filename with all spaces replaced by underscores
            safe_event_name = event['name'].replace(' ', '_').replace('/', '_').replace('\\', '_').replace('\'', '_').replace(':', '_').replace('(', '_').replace(')', '_').replace('#', '_')
            image_filename = f"event_images/{safe_event_name}.webp"

            # Update event data with local path
            event["imageUrl"] = "/" + image_filename

            if os.path.exists(image_filename):
                #print(f"Image already exists: {image_filename}, skipping download.")
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
        
    nonerror_upcoming_events = []
    midnight_today = datetime.datetime.now(est_timezone).replace(hour=0, minute=0, second=0, microsecond=0)

    for event in upcoming_events:
        startDate = event.get("startDate")
        if not startDate:
            print(f'{event.get("name")} missing startdate ')
            continue
        
        startDateTime = parse(event["startDate"])

        if startDateTime.date() == datetime.date(2025, 6, 28) and "unity" not in event.get("name", "").lower():
            print(f"Skipping event on June 28, 2025: {event['name']}")
            continue

        if startDateTime > midnight_today:
            nonerror_upcoming_events = [event] + nonerror_upcoming_events
        else:
            print(f'{event.get("name")} already happened ')


    unique_events = []
    fields_to_compare = ['name', 'description', 'url', 'imageUrl', 'startDate', 'endTime']

    for event in nonerror_upcoming_events:
        is_duplicate = False
        for unique_event in unique_events:
            if sum(event.get(field) == unique_event.get(field) for field in fields_to_compare) >= 4:
                is_duplicate = True
                print(f'Duplicate event {event.get("name")}')
                break
        if not is_duplicate:
            unique_events.append(event)


    # Save upcoming events to a file
    with open("upcoming_events.json", "w+", encoding="utf-8") as f:
        json.dump(unique_events, f, indent=4)
        print(f"Upcoming events saved to upcoming_events.json")

    events_to_ics(unique_events, output_file="baltimore_tech_events.ics")