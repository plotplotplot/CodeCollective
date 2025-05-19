import genCalendar
import json

import json
from ics import Calendar, Event
import datetime
import pytz
from html import escape
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
        
        # Process description - convert markdown to HTML
        description = event_data.get('description', '')
        html_description = parse_markdown_to_html(description)
        
        # Add location and URL information to description
        location_info = event_data.get('location', {})
        location_str = ""
        if location_info:
            location_parts = [
                location_info.get('name', ''),
                location_info.get('address', ''),
                f"{location_info.get('city', '')}, {location_info.get('state', '')} {location_info.get('country', '')}"
            ]
            location_str = ", ".join([p for p in location_parts if p and p.strip()])
        
        # Add group name if available
        group_name = event_data.get('group', '')
        group_info = f"<p><b>Group:</b> {group_name}</p>" if group_name else ""
        
        # Combine all information for the description
        full_description = f"""
        {html_description}
        
        <p><b>Event Link:</b> <a href="{event_data.get('url', '')}">{event_data.get('url', '')}</a></p>
        {group_info}
        """
        event.description = full_description
        
        # Set date/time information
        start_str = event_data.get('startDate')
        end_str = event_data.get('endTime')
        
        if start_str:
            # Parse ISO format dates
            try:
                start_time = datetime.datetime.fromisoformat(start_str)
                event.begin = start_time
                
                if end_str:
                    end_time = datetime.datetime.fromisoformat(end_str)
                    event.end = end_time
                else:
                    # Default to 2 hours if no end time specified
                    event.end = start_time + datetime.timedelta(hours=2)
            except ValueError as e:
                print(f"Error parsing date for event {event.name}: {e}")
                continue
        
        # Set location
        event.location = location_str
        
        # Set URL
        event.url = event_data.get('url', '')
        
        # Add to calendar
        cal.events.add(event)
    
    # Write the calendar to a file
    with open(output_file, 'w') as f:
        f.write(str(cal))
    
    print(f"Calendar with {len(cal.events)} events saved to {output_file}")
    return output_file

if __name__ == "__main__":
    meetup_urls = [
        "https://www.meetup.com/code-collective/events/",
        "https://www.meetup.com/baltimore-tech/events/",
        "https://www.meetup.com/devops-columbia/events/",
        "https://www.meetup.com/baltimore-code-and-coffee/events/",
        "https://www.meetup.com/baltimore-indie-game-developers-group/events/",
        "https://www.meetup.com/baltimore-cryptomondays/events/",
        "https://www.meetup.com/ellicott-city-cryptocurrency-meetup-group/events/",
        "https://www.meetup.com/it-social-east-us-ca-data-technology-cybersecurity/events/",
        "https://www.meetup.com/the-baltimore-wordpress-group/events/",
        "https://www.meetup.com/baltimore-bayesians/events/"
        "https://www.meetup.com/dataworks/events/"
    ]



    upcoming_events = []

    # Loop through each meetup URL
    for MEETUP_URL in meetup_urls:

        # Fetch upcoming events
        upcoming_page_content = genCalendar.fetch_meetup_page(MEETUP_URL)
        with open("meetup_upcoming.html", "w+", encoding="utf-8") as f:
            f.write(upcoming_page_content)

        # Extract the __NEXT_DATA__ JSON for upcoming events
        upcoming_next_data = genCalendar.extract_next_data(upcoming_page_content)
        
        # Parse upcoming events
        upcoming_events += genCalendar.parse_meetup_events(upcoming_next_data, include_past=True)

    # Save upcoming events to a file
    with open("upcoming_events.json", "w+", encoding="utf-8") as f:
        json.dump(upcoming_events, f, indent=4)
        print(f"Upcoming events saved to upcoming_events.json")
        events_to_ics(upcoming_events, output_file="baltimore_tech_events.ics")
