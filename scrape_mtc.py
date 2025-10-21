import requests
from bs4 import BeautifulSoup
import json
import hashlib
from datetime import datetime
from urllib.parse import urljoin

def scrape_mtc_events(url="https://members.mdtechcouncil.com/eventcalendar"):
    """
    Scrapes events from Maryland Tech Council event calendar
    
    Args:
        url: URL of the event calendar page
        
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
            
            # Check if event has registration button
            register_btn = block.find('a', class_='mn-button', string=lambda x: x and 'Register' in x)
            status = "ACTIVE" if register_btn else "ACTIVE"
            
            event = {
                "id": event_id,
                "name": event_name,
                "startDate": start_date,
                "endTime": end_date,
                "description": description,
                "url": event_url,
                "status": status,
                "location": {
                    "name": "",
                    "address": ""
                },
                "imageUrl": "https://mdtechcouncil.com/wp-content/uploads/2019/12/mtc-logo-home2.png",
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
    events = scrape_mtc_events()
    
    # Print results as JSON
    print(json.dumps(events, indent=4))
    
    # Optionally save to file
    with open('mtc_events.json', 'w') as f:
        json.dump(events, f, indent=4)
    
    print(f"\nScraped {len(events)} events successfully!")