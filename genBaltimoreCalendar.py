import scrape_meetup
import scrape_eventbrite
import scrape_jotform
import scrape_equitech
import json
from ics import Calendar, Event
import datetime
import pytz
from bs4 import BeautifulSoup
import re
import markdown

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
        
        # Process description - use BeautifulSoup for HTML extraction
        description = event_data.get('description', '')
        
        # First extract clean text from HTML using BeautifulSoup
        clean_description = extract_text_from_html(description)
        
        # Then parse any remaining markdown
        plain_description = parse_markdown_to_plain_text(clean_description)
        
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
                # Handle different ISO format variations
                if start_str.endswith('Z'):
                    start_time = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                else:
                    start_time = datetime.datetime.fromisoformat(start_str)
                
                event.begin = start_time
                
                if end_str:
                    if end_str.endswith('Z'):
                        end_time = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    else:
                        end_time = datetime.datetime.fromisoformat(end_str)
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
    with open("./manual_events.json", "r") as f:
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
        print(f"Fetching events from {EVENTBRITE_URL}")
        upcoming_events += [scrape_eventbrite.parse_eventbrite_event(EVENTBRITE_URL)]

    for JOTFORM_URL in sources.get("Jotform", []):
        print(f"Fetching events from {JOTFORM_URL}")
        upcoming_events += [scrape_jotform.parse_jotform_event(JOTFORM_URL)]

    upcoming_events += scrape_equitech.scrape_equitech_tuesday()

    for event in upcoming_events:
        # Download images if available
        if "imageUrl" in event and event["imageUrl"]:
            image_url = event["imageUrl"]
            extension = extract_proper_extension(image_url)
            
            # Create a valid filename with all spaces replaced by underscores
            safe_event_name = event['name'].replace(' ', '_').replace('/', '_').replace('\\', '_')
            image_filename = f"event_images/{safe_event_name}.{extension}"
        
    # Save upcoming events to a file
    with open("upcoming_events.json", "w+", encoding="utf-8") as f:
        json.dump(upcoming_events, f, indent=4)
        print(f"Upcoming events saved to upcoming_events.json")
    events_to_ics(upcoming_events, output_file="baltimore_tech_events.ics")