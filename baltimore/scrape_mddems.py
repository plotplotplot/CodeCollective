"""
Scraper for Maryland Democratic Party events
https://mddems.org/events/
"""

import requests
import re
import json
from datetime import datetime
from typing import List, Dict, Optional


def fetch_page(url: str) -> Optional[str]:
    """Fetch webpage content"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def parse_event_date(date_str: str) -> tuple:
    """
    Parse event date string like '23, March 2026 / 10:00pm EDT'
    Returns (start_date_iso, end_date_iso)
    """
    try:
        # Extract date and time parts
        # Format: "23, March 2026 / 10:00pm EDT"
        parts = date_str.split(' / ')
        if len(parts) != 2:
            return None, None
        
        date_part = parts[0].strip()  # "23, March 2026"
        time_part = parts[1].strip()  # "10:00pm EDT"
        
        # Remove timezone from time part
        time_clean = time_part.replace('EDT', '').replace('EST', '').strip()
        
        # Parse the combined datetime
        # Format: "23, March 2026 10:00pm"
        dt_str = f"{date_part} {time_clean}"
        dt = datetime.strptime(dt_str, "%d, %B %Y %I:%M%p")
        
        # Create ISO format with timezone
        start_date = dt.strftime("%Y-%m-%dT%H:%M:%S-04:00")
        
        # Default end time is 2 hours after start
        from datetime import timedelta
        end_dt = dt + timedelta(hours=2)
        end_date = end_dt.strftime("%Y-%m-%dT%H:%M:%S-04:00")
        
        return start_date, end_date
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None, None


def format_address(address_str: str) -> Dict:
    """
    Format address string into location dict
    Example: "10405 O'Donnell Pl +Waldorf+MD+20603"
    """
    # Clean up the address - replace + with commas and spaces
    cleaned = address_str.replace(' +', ', ').replace('+', ' ')
    
    # Handle private addresses
    if "private" in cleaned.lower():
        return {
            "name": "Private Location",
            "address": "Maryland"
        }
    
    if not cleaned or cleaned.strip() == ",":
        return {
            "name": "Maryland Democratic Party Event",
            "address": "Maryland"
        }
    
    return {
        "name": cleaned.split(',')[0] if ',' in cleaned else cleaned,
        "address": cleaned
    }


def extract_events(html: str) -> List[Dict]:
    """Extract events from the HTML page"""
    events = []
    
    # Find the GeoJSON features containing events
    matches = re.findall(r'var features = (\[.*?\]);', html, re.DOTALL)
    
    if not matches:
        print("No event features found in page")
        return events
    
    for features_str in matches:
        try:
            features = json.loads(features_str)
            
            for feature in features:
                props = feature.get('properties', {})
                
                title = props.get('title', '')
                date_str = props.get('event_date', '')
                event_url = props.get('event_url', '')
                event_type = props.get('event_type', '')
                address_str = props.get('event_address', '')
                
                if not title or not date_str:
                    continue
                
                # Parse dates
                start_date, end_date = parse_event_date(date_str)
                if not start_date:
                    continue
                
                # Format location
                location = format_address(address_str)
                
                event = {
                    "name": title,
                    "startDate": start_date,
                    "endTime": end_date,
                    "description": f"Event type: {event_type}",
                    "url": event_url,
                    "status": "ACTIVE",
                    "location": location,
                }
                
                events.append(event)
                
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            continue
    
    # Remove duplicates based on name and start date
    seen = set()
    unique_events = []
    for event in events:
        key = (event.get('name', ''), event.get('startDate', ''))
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
    
    return unique_events


def scrape_events() -> List[Dict]:
    """
    Main scraping function for Maryland Democratic Party events
    
    Returns:
        List of event dictionaries in the standardized format
    """
    url = "https://mddems.org/events-iframe/"
    
    print(f"Fetching MD Dems events from {url}")
    html = fetch_page(url)
    
    if not html:
        print("Failed to fetch page")
        return []
    
    events = extract_events(html)
    print(f"Extracted {len(events)} unique events")
    
    return events


if __name__ == "__main__":
    events = scrape_events()
    
    # Print events for debugging
    print(f"\nFound {len(events)} events:")
    print("=" * 60)
    for i, event in enumerate(events, 1):
        print(f"{i}. {event['name']}")
        print(f"   Date: {event['startDate']}")
        print(f"   Location: {event['location']['address']}")
        print(f"   URL: {event['url']}")
        print("-" * 60)
    
    # Save to file for testing
    import json
    output_file = 'md_dems_events.json'
    with open(output_file, 'w') as f:
        json.dump(events, f, indent=2)
    print(f"\nSaved to {output_file}")
