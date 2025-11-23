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

def fetch_meetup_page(url):
    """Fetches the HTML content of the Meetup page."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise Exception(f"Failed to retrieve page: {e}")

def extract_next_data(html_content):
    """Extracts the __NEXT_DATA__ JSON from the HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
    
    if not next_data_script:
        raise Exception("Could not find __NEXT_DATA__ in the HTML")
    
    try:
        return json.loads(next_data_script.string)
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse __NEXT_DATA__ JSON: {e}")

def parse_meetup_events(next_data, include_past=False, source_url=None):
    """Parses events from the __NEXT_DATA__ structure, tagging each with the originating URL."""
    events = []
    hero_image_url = None
    
    try:
        apollo_state = next_data.get('props', {}).get('pageProps', {}).get('__APOLLO_STATE__', {})
        
        # Try multiple ways to find hero image
        group_keys = [key for key in apollo_state.keys() if key.startswith('Group:')]
        for group_key in group_keys:
            group_data = apollo_state.get(group_key, {})
            
            # Check group photo
            if 'groupPhoto' in group_data and group_data['groupPhoto']:
                photo_ref = group_data['groupPhoto'].get('__ref')
                if photo_ref and photo_ref in apollo_state:
                    photo_data = apollo_state.get(photo_ref, {})
                    hero_image_url = photo_data.get('highResUrl') or photo_data.get('baseUrl')
                    if hero_image_url: break
            
            # Check key photo
            if not hero_image_url and 'keyPhoto' in group_data and group_data['keyPhoto']:
                photo_ref = group_data['keyPhoto'].get('__ref')
                if photo_ref and photo_ref in apollo_state:
                    photo_data = apollo_state.get(photo_ref, {})
                    hero_image_url = photo_data.get('highResUrl') or photo_data.get('baseUrl')
                    if hero_image_url: break
            
            # Check cover photo
            if not hero_image_url and 'coverPhoto' in group_data and group_data['coverPhoto']:
                photo_ref = group_data['coverPhoto'].get('__ref')
                if photo_ref and photo_ref in apollo_state:
                    photo_data = apollo_state.get(photo_ref, {})
                    hero_image_url = photo_data.get('highResUrl') or photo_data.get('baseUrl')
                    if hero_image_url: break
        
        # Parse events
        event_keys = [key for key in apollo_state.keys() if key.startswith('Event:')]
        
        for event_key in event_keys:
            event_data = apollo_state.get(event_key, {})
            if event_data.get('__typename') == 'Event':
                event = {
                    "id": event_data.get('id'),
                    "name": event_data.get('title'),
                    "description": event_data.get('description'),
                    "startDate": event_data.get('dateTime'),
                    "endTime": event_data.get('endTime'),
                    "url": event_data.get('eventUrl'),
                    "status": event_data.get('status'),
                    "source": source_url,
                }
                
                # Get venue information
                if 'venue' in event_data and event_data['venue']:
                    venue_ref = event_data['venue'].get('__ref')
                    if venue_ref and venue_ref in apollo_state:
                        venue_data = apollo_state.get(venue_ref, {})
                        event['location'] = {
                            'name': venue_data.get('name', ''),
                            'address': venue_data.get('address', ''),
                            'city': venue_data.get('city', ''),
                            'state': venue_data.get('state', ''),
                            'country': venue_data.get('country', '')
                        }
                
                # Get event image
                event_image_url = None
                if 'featuredEventPhoto' in event_data and event_data['featuredEventPhoto']:
                    image_ref = event_data['featuredEventPhoto'].get('__ref')
                    if image_ref and image_ref in apollo_state:
                        image_data = apollo_state.get(image_ref, {})
                        event_image_url = image_data.get('highResUrl') or image_data.get('baseUrl')
                
                # Use hero image as fallback
                event['imageUrl'] = event_image_url or hero_image_url
                
                if include_past or event_data.get('status') == 'ACTIVE':
                    events.append(event)
    
    except Exception as e:
        print(f"Error parsing events: {str(e)}")
    
    return events

def create_html(events, header_title="Events for Baltimore Code Collective"):
    """Creates an HTML string for the events."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{header_title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }}
            .event-card {{
                display: flex;
                margin-bottom: 30px;
                border: 1px solid #ddd;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .event-image {{
                flex: 0 0 300px;
            }}
            .event-thumbnail {{
                width: 100%;
                height: 100%;
                object-fit: cover;
            }}
            .event-content {{
                flex: 1;
                padding: 20px;
            }}
            .event-title {{
                margin: 10px 0;
                font-size: 1.5em;
            }}
            .event-date {{
                color: #666;
                margin-bottom: 5px;
            }}
            .event-location {{
                color: #666;
                margin-bottom: 15px;
            }}
            .event-description {{
                margin: 15px 0;
                max-height: 100px;
                overflow: hidden;
                transition: max-height 0.3s ease;
            }}
            .event-description.expanded {{
                max-height: none;
            }}
            .see-more {{
                color: #0066cc;
                cursor: pointer;
                display: inline-block;
                margin-top: 5px;
            }}
            .rsvp-button, .share-button {{
                padding: 8px 15px;
                margin-right: 10px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            .rsvp-button {{
                background-color: #f64060;
                color: white;
            }}
            .share-button {{
                background-color: #e0e0e0;
            }}
            .divider {{
                border: none;
                border-top: 1px solid #eee;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <h1>{header_title}</h1>
        <p><a href="https://www.meetup.com/code-collective/">Join our Meetup!</a></p>
    """
    
    if not events:
        html_content += "<p>No events to display at this time.</p>"
    else:
        for event in events:
            event_name = escape(event.get("name", "No title available"))
            event_date = event.get("startDate", "No date available")
            
            # Handle date conversion
            try:
                if event_date:
                    # Remove timezone indicator if present
                    event_date = event_date.replace('Z', '') if event_date.endswith('Z') else event_date
                    
                    if 'T' in event_date:
                        # Parse ISO format date
                        if '+' in event_date or '-' in event_date and event_date.rindex('-') > event_date.index('T'):
                            event_date_obj = datetime.datetime.fromisoformat(event_date)
                        else:
                            event_date_obj = datetime.datetime.fromisoformat(event_date)
                            event_date_obj = utc_timezone.localize(event_date_obj)
                        
                        # Convert to EST
                        event_date_est = event_date_obj.astimezone(est_timezone)
                        event_date = event_date_est.strftime("%A, %B %d, %Y at %I:%M %p")
            except Exception as e:
                print(f"Error parsing date {event_date}: {e}")
                event_date = "Date parsing error"

            event_description = escape(event.get("description", "No description available"))
            event_description = markdown.markdown(event_description).replace("strong>", "b>")
            
            event_location = event.get("location", {}).get("name", "No location available")
            event_link = event.get("url", "#")
            event_image = event.get("imageUrl", "")
            
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
    
    html_content += """
        <script>
            function toggleDescription(element) {
                const description = element.previousElementSibling;
                description.classList.toggle('collapsed');
                element.textContent = description.classList.contains('collapsed') ? 'See more' : 'See less';
            }
        </script>
    </body>
    </html>
    """
    return html_content

def save_html_file(content, filename="calendar.html"):
    """Saves the HTML content to a file."""
    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"HTML file saved as {filename}")
    except IOError as e:
        print(f"Failed to save HTML file: {e}")

if __name__ == "__main__":
    try:
        # URL of the Baltimore Code Collective Meetup group
        MEETUP_URL = "https://www.meetup.com/code-collective/events/"
        PAST_EVENTS_URL = "https://www.meetup.com/code-collective/events/?type=past"

        # Fetch upcoming events
        upcoming_page_content = fetch_meetup_page(MEETUP_URL)
        upcoming_next_data = extract_next_data(upcoming_page_content)
        upcoming_events = parse_meetup_events(upcoming_next_data, source_url=MEETUP_URL)

        # Fetch past events
        past_page_content = fetch_meetup_page(PAST_EVENTS_URL)
        past_next_data = extract_next_data(past_page_content)
        past_events = parse_meetup_events(past_next_data, include_past=True, source_url=PAST_EVENTS_URL)

        # Create HTML content
        upcoming_html = create_html(upcoming_events, "Upcoming Events for Baltimore Code Collective")
        past_html = create_html(past_events, "Past Events for Baltimore Code Collective")
        complete_html = upcoming_html + past_html
        
        # Save the HTML file
        save_html_file(complete_html)
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
