import json
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

def fetch_and_parse_luma_events(url: str) -> List[Dict[str, Any]]:
    """
    Fetch a Luma URL and parse events from it.
    
    Args:
        url (str): The Luma URL to fetch and parse
        
    Returns:
        List[Dict[str, Any]]: List of parsed events in the specified format
    """
    # Add headers to mimic a real browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    # Fetch the URL
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()  # Raise an exception for bad status codes
    
    # Parse the HTML content
    return parse_luma_events(response.text)
        

def parse_luma_events(html_content: str) -> List[Dict[str, Any]]:
    """
    Parse events from Luma HTML content and return them in the specified format.
    
    Args:
        html_content (str): The HTML content containing JSON-LD structured data
        
    Returns:
        List[Dict[str, Any]]: List of parsed events in the specified format
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the JSON-LD script tag
    json_ld_script = soup.find('script', {'type': 'application/ld+json'})
    
    if not json_ld_script:
        return []
    
    try:
        # Parse the JSON-LD data
        json_data = json.loads(json_ld_script.string)
        
        # Extract events from the JSON-LD data
        events = json_data.get('events', [])
        
        parsed_events = []
        
        for event in events:
            parsed_event = parse_single_event(event)
            if parsed_event:
                parsed_events.append(parsed_event)
                
        return parsed_events
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON-LD: {e}")
        return []

def parse_single_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a single event from JSON-LD format to the target format.
    
    Args:
        event (Dict[str, Any]): Single event data from JSON-LD
        
    Returns:
        Optional[Dict[str, Any]]: Parsed event in target format, or None if parsing fails
    """
    # Extract basic event information
    name = event.get('name', '')
    description = event.get('description', '')
    start_date = event.get('startDate', '')
    end_date = event.get('endDate', '')
    event_url = event.get('@id', '')
    
    # Determine status based on eventStatus
    event_status = event.get('eventStatus', '')
    status = 'ACTIVE' if 'EventScheduled' in event_status else 'INACTIVE'
    
    # Extract location information
    location_data = event.get('location', {})
    location = parse_location(location_data)
    
    # Extract image URL
    images = event.get('image', [])
    image_url = images[0] if images and isinstance(images, list) else ''
    
    # Build the parsed event
    parsed_event = {
        'name': name,
        'description': description,
        'startDate': start_date,
        'endTime': end_date,  # Note: using endTime as per the target format
        'url': event_url,
        'status': status,
        'location': location,
        'imageUrl': image_url
    }
    
    return parsed_event
    

def parse_location(location_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Parse location information from JSON-LD format.
    
    Args:
        location_data (Dict[str, Any]): Location data from event
        
    Returns:
        Dict[str, str]: Parsed location with name and address
    """
    location = {
        'name': '',
        'address': ''
    }
    
    if not location_data:
        return location
    
    # Extract location name
    location['name'] = location_data.get('name', '')
    
    # Extract address information
    address_data = location_data.get('address', {})
    if isinstance(address_data, dict):
        address_parts = []
        
        # Build address from components
        street_address = address_data.get('streetAddress', '')
        locality = address_data.get('addressLocality', '')
        region = address_data.get('addressRegion', '')
        country_data = address_data.get('addressCountry', {})
        
        if street_address:
            address_parts.append(street_address)
        if locality:
            address_parts.append(locality)
        if region:
            address_parts.append(region)
        
        # Handle country (could be string or object)
        if isinstance(country_data, dict):
            country_name = country_data.get('name', '')
            if country_name and country_name != 'United States':
                address_parts.append(country_name)
        elif isinstance(country_data, str) and country_data != 'United States':
            address_parts.append(country_data)
        
        location['address'] = ', '.join(address_parts)
    
    elif isinstance(address_data, str):
        # If the address is a plain string, just use it directly
        location['address'] = address_data

    return location


def parse_multiple_urls(urls: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse events from multiple Luma URLs.
    
    Args:
        urls (List[str]): List of Luma URLs to parse
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionary mapping URLs to their parsed events
    """
    results = {}
    
    for url in urls:
        print(f"Processing: {url}")
        events = fetch_and_parse_luma_events(url)
        results[url] = events
        print(f"Found {len(events)} events")
        
    return results

import sys
if __name__ == "__main__":

    """
    Example usage of the parser with a Luma URL.
    """
    # Example URL
    url = "https://lu.ma/user/charmcityjs"
    
    print(f"Fetching and parsing events from: {url}")
    print("=" * 60)
    
    # Fetch and parse events from the URL
    events = fetch_and_parse_luma_events(url)
    
    if not events:
        print("No events found or error occurred.")
        sys.exit(1)
    
    print(f"Found {len(events)} event(s):")
    print("=" * 60)
    
    # Print the results
    for i, event in enumerate(events, 1):
        print(f"Event {i}:")
        print(json.dumps(event, indent=2))
        print("-" * 50)