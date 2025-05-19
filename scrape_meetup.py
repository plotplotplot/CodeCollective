import requests
import json
from bs4 import BeautifulSoup
import datetime
import re
import pytz
import markdown
from html import escape

# Define the timezone for EST
utc_timezone = pytz.timezone("UTC")
est_timezone = pytz.timezone("America/New_York")

# URL of the Baltimore Code Collective Meetup group
MEETUP_URL = "https://www.meetup.com/code-collective/events/"
PAST_EVENTS_URL = "https://www.meetup.com/code-collective/events/?type=past"

def fetch_meetup_page(url):
    """Fetches the HTML content of the Meetup page."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve page: {response.status_code}")
    return response.text

def extract_next_data(html_content):
    """
    Extracts the __NEXT_DATA__ JSON from the HTML which contains all the event data
    in modern Meetup pages.
    """
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_content, re.DOTALL)
    if not next_data_match:
        raise Exception("Could not find __NEXT_DATA__ in the HTML")
    
    next_data_json = next_data_match.group(1)
    try:
        next_data = json.loads(next_data_json)
        return next_data
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse __NEXT_DATA__ JSON: {e}")

def parse_meetup_events(next_data, include_past=False):
    """
    Parses events from the __NEXT_DATA__ structure of the modern Meetup page.
    
    Args:
        next_data (dict): The parsed __NEXT_DATA__ from the Meetup page
        include_past (bool): Whether to include past events (status != 'ACTIVE')
        
    Returns:
        list: List of event dictionaries containing event details
    """
    events = []
    
    try:
        # Navigate through the nested structure to find events
        apollo_state = next_data.get('props', {}).get('pageProps', {}).get('__APOLLO_STATE__', {})
        
        # Find all event objects in the Apollo state
        event_keys = [key for key in apollo_state.keys() if key.startswith('Event:')]
        
        for event_key in event_keys:
            event_data = apollo_state.get(event_key, {})
            if event_data.get('__typename') == 'Event':
                # Extract the event details
                event = {
                    "id": event_data.get('id'),
                    "name": event_data.get('title'),
                    "description": event_data.get('description'),
                    "startDate": event_data.get('dateTime'),
                    "endTime": event_data.get('endTime'),
                    "url": event_data.get('eventUrl'),
                    "status": event_data.get('status'),
                }
                
                # Get venue information
                venue_ref = event_data.get('venue', {}).get('__ref')
                if venue_ref and venue_ref in apollo_state:
                    venue_data = apollo_state.get(venue_ref, {})
                    event['location'] = {
                        'name': venue_data.get('name', ''),
                        'address': venue_data.get('address', ''),
                        'city': venue_data.get('city', ''),
                        'state': venue_data.get('state', ''),
                        'country': venue_data.get('country', '')
                    }
                
                # Get image information
                image_ref = event_data.get('featuredEventPhoto', {}).get('__ref')
                if image_ref and image_ref in apollo_state:
                    image_data = apollo_state.get(image_ref, {})
                    event['imageUrl'] = image_data.get('highResUrl')
                
                # Include all events if include_past is True, otherwise only active events
                if include_past or event_data.get('status') == 'ACTIVE':
                    events.append(event)
        
    except Exception as e:
        print(f"Error parsing events: {e}")
    
    return events

def create_html(events, header_title="Events for Baltimore Code Collective"):
    """Creates an HTML string for the events, including event images."""
    html_content = f"<h1>{header_title}</h1>"
    html_content += '<a href="https://www.meetup.com/code-collective/">Join our Meetup!</a>'

    if not events:
        html_content += "<p>No events to display at this time.</p>"
    else:
        for event in events:
            print(json.dumps(event, indent=2))
            event_name = escape(event.get("name", "No title available"))
            event_date = event.get("startDate", "No date available")
            
            # Handle date conversion
            try:
                # Remove timezone indicator if present
                event_date = event_date.replace('Z', '') if event_date.endswith('Z') else event_date
                
                # Parse ISO format date
                if 'T' in event_date:
                    # Check if there's a timezone offset
                    if '+' in event_date or '-' in event_date and event_date.rindex('-') > event_date.index('T'):
                        # Already has timezone information
                        event_date_obj = datetime.datetime.fromisoformat(event_date)
                        # Convert to EST
                        event_date_est = event_date_obj.astimezone(est_timezone)
                    else:
                        # No timezone information, assume UTC
                        event_date_obj = datetime.datetime.fromisoformat(event_date)
                        # Localize to UTC first
                        event_date_obj = utc_timezone.localize(event_date_obj)
                        # Then convert to EST
                        event_date_est = event_date_obj.astimezone(est_timezone)
                    
                    # Format the date
                    event_date = event_date_est.strftime("%Y-%m-%d %H:%M:%S")
                
            except Exception as e:
                print(f"Error parsing date {event_date}: {e}")
                event_date = "Date parsing error"

            event_description = escape(
                event.get("description", "No description available")
            )
            event_description = markdown.markdown(event_description).replace("strong>", "b>")

            event_location = event.get("location", {}).get(
                "name", "No location available"
            )
            event_link = event.get("url", "#")
            
            # Get the image URL, with fallback to None if not available
            event_image = event.get("imageUrl")
            image_html = ""
            if event_image:
                image_html = f"""
                    <div class="event-image">
                        <img src="{event_image}" alt="{event_name}" class="event-thumbnail">
                    </div>
                """
                
            html_content += f"""
                <div class="event-card">
                    {image_html}
                    <div class="event-content">
                        <div class="event-detail">
                            <h4 class="event-date">{event_date} EST</h4>
                            <p class="event-location">@{event_location}</p>
                        </div>
                        <h2 class="event-title">
                            <a href="{event_link}" target="_blank">{event_name}</a>
                        </h2>
                        <div class="event-details">
                            <div class="event-description collapsed">{event_description}</div>
                            <span class="see-more" onclick="toggleDescription(this)">See more</span>
                        </div>
                        <div class="event-actions">
                            <button class="rsvp-button">RSVP</button>
                            <button class="share-button">Share</button>
                        </div>
                    </div>
                </div>
                <hr class="divider">
            """
    return html_content


def save_html_file(content, filename="calendar.html"):
    """Saves the HTML content to a file."""
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"HTML file saved as {filename}")


if __name__ == "__main__":
    # Fetch upcoming events
    upcoming_page_content = fetch_meetup_page(MEETUP_URL)
    with open("meetup_upcoming.html", "w+", encoding="utf-8") as f:
        f.write(upcoming_page_content)

    # Extract the __NEXT_DATA__ JSON for upcoming events
    upcoming_next_data = extract_next_data(upcoming_page_content)
    
    # Parse upcoming events
    upcoming_events = parse_meetup_events(upcoming_next_data)

    # Fetch past events
    past_page_content = fetch_meetup_page(PAST_EVENTS_URL)
    with open("meetup_past.html", "w+", encoding="utf-8") as f:
        f.write(past_page_content)
    
    # Extract the __NEXT_DATA__ JSON for past events
    past_next_data = extract_next_data(past_page_content)
    
    # Parse past events
    past_events = parse_meetup_events(past_next_data, include_past=True)

    # Create HTML content for upcoming events
    upcoming_html = create_html(upcoming_events, header_title="Upcoming Events for Baltimore Code Collective")

    # Create HTML content for past events
    past_html = create_html(past_events, header_title="Past Events for Baltimore Code Collective")

    # Combine both upcoming and past events
    complete_html = upcoming_html + past_html
    
    try:
        with open("templates/events-template.html", "r", encoding="utf-8") as f:
            html_template = f.read()

        # Save the HTML content to a file
        save_html_file(html_template.replace("EVENTS_HTML", complete_html))
    except FileNotFoundError:
        # If the template file doesn't exist, just save the HTML content directly
        save_html_file(complete_html)