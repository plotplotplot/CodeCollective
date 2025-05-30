import re
from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime

def parse_eventbrite_event(url):
    """
    Parse an Eventbrite event page and extract key information.
    
    Args:
        url (str): URL of the Eventbrite event
        
    Returns:
        dict: Dictionary containing event details
    """
    # Make request to the event page
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": f"Failed to retrieve page: {response.status_code}"}
    
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract event ID from the URL
    event_id = url.split('-')[-1].split('/')[0]
    if not event_id.isdigit():
        event_id = re.search(r'tickets-(\d+)', url).group(1)
    
    # Extract event name
    try:
        event_name = soup.select_one('h1.event-title').text.strip()
    except:
        print("Event Over")
        return []
    
    # Extract event description
    try:
        event_description = soup.select_one('p.summary').text.strip()
    except:
        # If the specific 'summary' class isn't found, try to find another description
        description_el = soup.select_one('.eds-text--left p')
        event_description = description_el.text.strip() if description_el else ""
    
    # Extract event dates
    meta_tags = soup.find_all('meta')
    
    start_date = None
    end_date = None
    for tag in meta_tags:
        if tag.get('property') == 'event:start_time':
            start_date = tag.get('content')
        elif tag.get('property') == 'event:end_time':
            end_date = tag.get('content')
    
    # Extract location details
    location = {}
    venue_name_el = soup.select_one('.location-info__address p.location-info__address-text')
    if venue_name_el:
        location['name'] = venue_name_el.text.strip()
    
    address_container = soup.select_one('.location-info__address')
    if address_container:
        # The address is often just text nodes in this container
        address_text = ''
        for content in address_container.contents:
            if isinstance(content, str) and content.strip():
                address_text += content.strip() + ' '
        address_text = address_text.strip()
        
        if address_text:
            location['address'] = address_text
            
            # Try to extract city, state, country
            # Typical format: City, State Zip
            location_match = re.search(r'([^,]+),\s*(\w+)\s+(\d+)', address_text)
            if location_match:
                location['city'] = location_match.group(1).strip()
                location['state'] = location_match.group(2).strip()
                location['country'] = 'US'  # Assuming US
    
    # Extract image URL
    image_url = None
    for tag in meta_tags:
        if tag.get('property') in ['og:image', 'twitter:image']:
            image_url = tag.get('content')
            break
    
    # Determine event status - for simplicity, we'll assume ACTIVE if it's in the future
    status = "ACTIVE"
    
    # Build the result dictionary
    event_data = {
        "id": event_id,
        "name": event_name,
        "description": event_description,
        "startDate": start_date,
        "endTime": end_date,
        "url": url,
        "status": status,
        "location": location,
        "imageUrl": image_url
    }
    
    return [event_data]

# Example usage
if __name__ == "__main__":
    event_url = "https://www.eventbrite.com/e/indie-game-fest-2025-tickets-1264402364509"
    event_data = parse_eventbrite_event(event_url)
    print(json.dumps(event_data, indent=4))