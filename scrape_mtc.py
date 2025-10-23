import requests
from bs4 import BeautifulSoup
import json
import hashlib
from datetime import datetime
from urllib.parse import urljoin
import time
import re

def scrape_event_details(event_url):
    """
    Scrape detailed information from an individual event page
    
    Returns:
        dict with startDate, endTime, location details
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(event_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        details = {
            'startDate': None,
            'endTime': None,
            'location_name': '',
            'location_address': ''
        }
        
        # Find the time block with class 'mn-hours'
        time_block = soup.find('div', class_='mn-hours')
        if time_block:
            date_div = time_block.find('div', class_='mn-date')
            if date_div:
                # Extract the span text which contains the full date/time
                date_span = date_div.find('span')
                if date_span:
                    time_text = date_span.get_text(strip=True)
                    # Pattern: "Thursday, October 30, 2025 (4:00 PM - 7:00 PM)"
                    match = re.search(r'(\w+,\s+\w+\s+\d+,\s+\d{4})\s+\((\d+:\d+\s+[AP]M)\s*-\s*(\d+:\d+\s+[AP]M)\)', time_text)
                    if match:
                        date_str = match.group(1)
                        start_time = match.group(2)
                        end_time = match.group(3)
                        
                        try:
                            # Parse start time
                            dt_start = datetime.strptime(f"{date_str} {start_time}", "%A, %B %d, %Y %I:%M %p")
                            details['startDate'] = dt_start.strftime("%Y-%m-%dT%H:%M:%S-04:00")
                            
                            # Parse end time
                            dt_end = datetime.strptime(f"{date_str} {end_time}", "%A, %B %d, %Y %I:%M %p")
                            details['endTime'] = dt_end.strftime("%Y-%m-%dT%H:%M:%S-04:00")
                        except Exception as e:
                            print(f"  Date parsing error: {e}")
        
        # Find location block with class 'mn-location-description'
        location_block = soup.find('div', class_='mn-location-description')
        if location_block:
            text_div = location_block.find('div', class_='mn-text')
            if text_div:
                # Get all text and split by newlines
                location_text = text_div.get_text('\n', strip=True)
                lines = [line.strip() for line in location_text.split('\n') if line.strip()]
                
                if len(lines) >= 1:
                    details['location_name'] = lines[0]
                    # Combine remaining lines as address
                    if len(lines) > 1:
                        details['location_address'] = ', '.join(lines[1:])
        
        return details
        
    except Exception as e:
        print(f"  Warning: Could not fetch details from {event_url}: {e}")
        return None

def scrape_mtc_events(url="https://members.mdtechcouncil.com/eventcalendar", fetch_details=True):
    """
    Scrapes events from Maryland Tech Council event calendar
    
    Args:
        url: URL of the event calendar page
        fetch_details: If True, fetches individual event pages for times/location
        
    Returns:
        List of event dictionaries
    """
    
    # Request the page
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return []
    
    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    events = []
    scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    
    # Find all event panes - these have multiple classes
    # Look for divs with both 'mn-block' and 'mn-pane' and 'mn-listing'
    event_blocks = soup.find_all('div', class_=lambda x: x and 'mn-pane' in x and 'mn-listing' in x)
    
    print(f"Found {len(event_blocks)} event blocks")
    
    # Debug: If no events found, print some info
    if len(event_blocks) == 0:
        print("\nDebugging - looking for any mn-block divs:")
        all_blocks = soup.find_all('div', class_=lambda x: x and 'mn-block' in x)
        print(f"Found {len(all_blocks)} mn-block divs")
        if all_blocks:
            print(f"First block classes: {all_blocks[0].get('class')}")
    
    for block in event_blocks:
        try:
            # Extract event title and URL
            title_link = block.find('a', class_='mn-main-heading')
            if not title_link:
                print("No title link found, skipping")
                continue
                
            event_name = title_link.get_text(strip=True)
            event_url = title_link.get('href', '')
            if event_url:
                event_url = urljoin(url, event_url)
            
            # Extract date - it's in a span with class 'mn-date'
            date_span = block.find('span', class_='mn-date')
            date_text = date_span.get_text(strip=True) if date_span else ""
            
            # If no mn-date span, look in mn-sub-heading
            if not date_text:
                sub_heading = block.find('span', class_='mn-sub-heading')
                if sub_heading:
                    date_text = sub_heading.get_text(strip=True)
            
            # Extract description
            desc_div = block.find('div', class_='mn-description')
            description = ""
            if desc_div:
                desc_text = desc_div.find('div', class_='mn-text')
                if desc_text:
                    # Get all text, cleaning up whitespace
                    description = ' '.join(desc_text.get_text(strip=True).split())
            
            # Generate unique ID from event name and date
            unique_string = f"{event_name}{date_text}"
            event_id = hashlib.md5(unique_string.encode()).hexdigest()[:20]
            
            # Parse dates (simplified - would need more robust parsing)
            start_date = parse_date_string(date_text)
            end_date = start_date  # Same as start if not specified
            location_name = ""
            location_address = ""
            
            # Check if event has registration button
            register_btn = block.find('a', class_='mn-button', string=lambda x: x and 'Register' in x)
            status = "ACTIVE" if register_btn else "ACTIVE"
            
            # Fetch detailed information from event page
            if fetch_details and event_url:
                print(f"  Fetching details from {event_url}...")
                event_details = scrape_event_details(event_url)
                time.sleep(0.5)  # Be polite, don't hammer the server
                
                if event_details:
                    if event_details['startDate']:
                        start_date = event_details['startDate']
                    if event_details['endTime']:
                        end_date = event_details['endTime']
                    if event_details['location_name']:
                        location_name = event_details['location_name']
                        location_address = event_details['location_address']
            
            event = {
                "id": event_id,
                "name": event_name,
                "startDate": start_date,
                "endTime": end_date,
                "description": description,
                "url": event_url,
                "status": status,
                "location": {
                    "name": location_name,
                    "address": location_address
                },
                "imageUrl": "",
                "recurring": False,
                "scrapeTime": scrape_time
            }
            
            events.append(event)
            print(f"✓ Scraped: {event_name[:50]}...")
            
        except Exception as e:
            print(f"Error parsing event: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return events

def parse_date_string(date_str):
    """
    Parse date string to ISO format
    Example: "Wednesday, October 1, 2025" -> "2025-10-01T00:00:00-04:00"
    """
    try:
        # Handle date ranges like "10/15/2025 - 12/1/2025"
        if ' - ' in date_str:
            date_str = date_str.split(' - ')[0].strip()
        
        # Try parsing different formats
        for fmt in ["%A, %B %d, %Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%dT00:00:00-04:00")
            except ValueError:
                continue
        
        # Return current date if parsing fails
        return datetime.now().strftime("%Y-%m-%dT00:00:00-04:00")
    except:
        return datetime.now().strftime("%Y-%m-%dT00:00:00-04:00")

# Main execution
if __name__ == "__main__":
    print("Scraping MTC Event Calendar...")
    print("Note: Setting fetch_details=True will scrape each event page for times/location")
    print("This will be slower but more accurate.\n")
    
    # Set to True to fetch detailed times and location (slower)
    # Set to False for quick scraping (times will be midnight)
    events = scrape_mtc_events(fetch_details=True)
    
    # Print results as JSON
    print("\n" + "="*60)
    print(json.dumps(events, indent=4))
    
    # Optionally save to file
    with open('mtc_events.json', 'w') as f:
        json.dump(events, f, indent=4)
    
    print(f"\nScraped {len(events)} events successfully!")
    print(f"Saved to mtc_events.json")