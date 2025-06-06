import requests
from bs4 import BeautifulSoup
import json
import uuid
from datetime import datetime, timedelta, date

def scrape_equitech_tuesday():
    # URL to scrape
    url = "https://upsurgebaltimore.com/equitech-tuesday/"
    
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to fetch the page. Status code: {response.status_code}")
        return []
    
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all event sections
    # Looking for call-to-action sections that contain event information
    event_sections = soup.find_all('section', class_='site-section dark call-to-action')
    
    events = []
    
    # Counter for the events
    event_count = 0
    
    for event_section in event_sections:
        # Skip the email signup section
        if "Join the Equitech Tuesday mailing list" in event_section.text:
            continue
        
        # Extract event details
        event = {}
        
        # Extract event name (h2 text)
        name_element = event_section.find('h2', class_='title h2 fade-up')
        if name_element:
            event["name"] = name_element.text.strip()
        else:
            continue  # Skip if no name found
        
        # Extract location
        location_element = event_section.find('div', class_='title subtitle-color fade-up')
        location_name = location_element.text.strip() if location_element else "Unknown Location"
        
        # Extract image if available
        image_element = event_section.find('img')
        image_url = image_element.get('src') if image_element else ""
        
        # Calculate the date for this event (first event is next Tuesday, then add 7 days for each subsequent event)
        if "Carroll" in event["name"]:
            event_date = datetime.strptime('2025-05-20', '%Y-%m-%d').date()
        elif "Content" in event["name"]:
            event_date = datetime.strptime('2025-05-27', '%Y-%m-%d').date()
        elif "Summit" in event["name"]:
            event_date = datetime.strptime('2025-06-03', '%Y-%m-%d').date()
        elif "ESOs" in event["name"]:
            event_date = datetime.strptime('2025-06-10', '%Y-%m-%d').date()
        else:
            print("Event lost. Get the real calendar doc!")
            break
        
        # Convert date to datetime if it's just a date object
        if isinstance(event_date, date) and not isinstance(event_date, datetime):
            # Convert date to datetime at midnight
            event_date = datetime.combine(event_date, datetime.min.time())
        
        # Set the time to 6PM (common start time for events)
        start_datetime = event_date.replace(hour=18, minute=0, second=0)
        end_datetime = event_date.replace(hour=20, minute=0, second=0)
        
        # Format dates for JSON
        event["startDate"] = start_datetime.strftime("%Y-%m-%dT%H:%M:%S-04:00")
        event["endTime"] = end_datetime.strftime("%Y-%m-%dT%H:%M:%S-04:00")
        
        # Set description based on the event name and location
        event["description"] = f"Equitech Tuesday event at {location_name}: {event['name']}. Join Baltimore's tech ecosystem for networking and innovation."
        
        # Set URL to the Equitech Tuesday page
        event["url"] = url
        
        # Set status as ACTIVE
        event["status"] = "ACTIVE"
        
        # Set location details
        event["location"] = {
            "name": location_name,
            "address": f"{location_name}, Baltimore, MD 21202",
            "city": "Baltimore",
            "state": "MD",
            "country": "US"
        }
        
        # Set image URL
        event["imageUrl"] = image_url
        
        events.append(event)
        
        # Increment the event counter
        event_count += 1
    
    return events

def main():
    events = scrape_equitech_tuesday()
    
    # Print the results as formatted JSON
    print(json.dumps(events, indent=4))
    
    # Optionally save to a file
    with open('equitech_events.json', 'w') as f:
        json.dump(events, f, indent=4)
    
    print(f"Scraped {len(events)} events and saved to equitech_events.json")

if __name__ == "__main__":
    main()