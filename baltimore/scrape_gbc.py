import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from urllib.parse import urljoin

def scrape_gbc_events():
    """
    Scrapes events from GBC events list page and returns formatted JSON
    """
    url = "https://gbc.org/events/list/"
    
    try:
        # Send GET request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        
        # Find all event articles
        event_articles = soup.find_all('article', class_='tribe-events-calendar-list__event')
        
        for article in event_articles:
            try:
                event_data = extract_event_data(article, url)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                print(f"Error processing event: {e}")
                continue
        
        return events
        
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return []

def extract_event_data(article, base_url):
    """
    Extract event data from a single event article element
    """
    # Get event title and URL
    title_link = article.find('a', class_='tribe-events-calendar-list__event-title-link')
    if not title_link:
        return None
        
    name = title_link.get_text(strip=True)
    event_url = title_link.get('href', '')
    
    # Get date and time information
    datetime_elem = article.find('time', class_='tribe-events-calendar-list__event-datetime')
    if not datetime_elem:
        return None
    
    # Extract date from datetime attribute
    date_attr = datetime_elem.get('datetime')
    if not date_attr:
        return None
    
    # Parse the time text to get start and end times
    time_text = datetime_elem.get_text(strip=True)
    start_date, end_date = parse_event_datetime(date_attr, time_text)
    
    # Get description
    description_elem = article.find('div', class_='tribe-events-calendar-list__event-description')
    description = ""
    if description_elem:
        # Get text and clean it up
        desc_text = description_elem.get_text(strip=True)
        # Remove "[...]" or similar continuation markers
        description = re.sub(r'\[.*?\]', '', desc_text).strip()
    
    # Get venue information
    venue_elem = article.find('address', class_='tribe-events-calendar-list__event-venue')
    location = extract_location_data(venue_elem)
    
    # Get event type (Virtual, In-Person, Hybrid)
    event_type = extract_event_type(article)
    
    # Get image URL
    image_elem = article.find('img', class_='tribe-events-calendar-list__event-featured-image')
    image_src = ""
    if image_elem:
        image_src = image_elem.get('src', '')
    
    # Build event object
    event_data = {
        "name": name,
        "startDate": start_date,
        "endTime": end_date,
        "description": description,
        "url": event_url,
        "status": "ACTIVE",
        "location": location,
        "imageUrl": image_src
    }
    
    return event_data

def parse_event_datetime(date_attr, time_text):
    """
    Parse date and time information to create ISO format datetime strings
    """
    # Extract date from datetime attribute (format: 2025-06-10)
    base_date = date_attr
    
    # Parse time text (format: "June 10 @ 6:00 pm - 8:00 pm")
    time_pattern = r'(\d{1,2}:\d{2})\s*(am|pm).*?(\d{1,2}:\d{2})\s*(am|pm)'
    time_match = re.search(time_pattern, time_text, re.IGNORECASE)
    
    if time_match:
        start_time = time_match.group(1)
        start_period = time_match.group(2).lower()
        end_time = time_match.group(3)
        end_period = time_match.group(4).lower()
        
        # Convert to 24-hour format
        start_hour_24 = convert_to_24_hour(start_time, start_period)
        end_hour_24 = convert_to_24_hour(end_time, end_period)
        
        # Create ISO datetime strings (assuming Eastern Time)
        start_date = f"{base_date}T{start_hour_24}-04:00"
        end_date = f"{base_date}T{end_hour_24}-04:00"
        
        return start_date, end_date
    
    # Fallback if time parsing fails
    return f"{base_date}T12:00:00-04:00", f"{base_date}T13:00:00-04:00"

def convert_to_24_hour(time_str, period):
    """
    Convert 12-hour time format to 24-hour format
    """
    hour, minute = time_str.split(':')
    hour = int(hour)
    
    if period == 'pm' and hour != 12:
        hour += 12
    elif period == 'am' and hour == 12:
        hour = 0
    
    return f"{hour:02d}:{minute}:00"

def extract_location_data(venue_elem):
    """
    Extract location information from venue element
    """
    location = {
        "name": "",
        "address": "",
        "city": "Baltimore",
        "state": "MD",
        "country": "US"
    }
    
    if venue_elem:
        venue_title = venue_elem.find('span', class_='tribe-events-calendar-list__event-venue-title')
        if venue_title:
            location["name"] = venue_title.get_text(strip=True)
        
        venue_address = venue_elem.find('span', class_='tribe-events-calendar-list__event-venue-address')
        if venue_address:
            address_text = venue_address.get_text(strip=True)
            location["address"] = address_text
            
            # Try to parse city and state from address
            if "Baltimore, MD" in address_text:
                location["city"] = "Baltimore"
                location["state"] = "MD"
    
    return location

def extract_event_type(article):
    """
    Extract event type from the event type pill
    """
    type_pill = article.find('div', class_='mg-events-type-pill')
    if type_pill:
        type_text = type_pill.get_text(strip=True)
        return type_text
    return "In-Person"  # Default

def main():
    """
    Main function to run the scraper and output JSON
    """
    print("Scraping GBC events...")
    events = scrape_gbc_events()
    
    if events:
        print(f"Found {len(events)} events")
        # Output as formatted JSON
        json_output = json.dumps(events, indent=2)
        print("\nEvents JSON:")
        print(json_output)
        
        # Optionally save to file
        with open('gbc_events.json', 'w') as f:
            json.dump(events, f, indent=2)
        print("\nEvents saved to gbc_events.json")
    else:
        print("No events found or error occurred")

if __name__ == "__main__":
    main()