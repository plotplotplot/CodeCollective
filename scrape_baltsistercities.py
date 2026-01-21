import json
import re
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
import requests

def parse_date_range(date_string):
    """Parse date range strings like 'September 21, 2025 – March 8, 2025'"""
    date_string = date_string.strip()
    
    # Handle date ranges
    if '–' in date_string or '-' in date_string:
        # Replace different dash types with standard dash
        date_string = date_string.replace('–', '-').replace('—', '-')
        parts = date_string.split('-')
        if len(parts) >= 2:
            start_date_str = parts[0].strip()
            end_date_str = parts[1].strip()
            
            # Try to parse dates
            date_formats = [
                "%B %d, %Y",  # September 21, 2025
                "%b %d, %Y",  # Sep 21, 2025
                "%Y-%m-%d",   # 2025-09-21
                "%m/%d/%Y"    # 09/21/2025
            ]
            
            for date_format in date_formats:
                try:
                    start_date = datetime.strptime(start_date_str, date_format)
                    end_date = datetime.strptime(end_date_str, date_format)
                    return start_date, end_date
                except ValueError:
                    continue
    else:
        # Single date
        date_formats = [
            "%B %d, %Y",  # September 21, 2025
            "%b %d, %Y",  # Sep 21, 2025
            "%Y-%m-%d",   # 2025-09-21
            "%m/%d/%Y"    # 09/21/2025
        ]
        
        for date_format in date_formats:
            try:
                date = datetime.strptime(date_string, date_format)
                return date, date
            except ValueError:
                continue
    
    return None, None

def extract_time_from_text(text):
    """Extract time information from text"""
    time_patterns = [
        r'Time:\s*<\/strong>([^<]+)',  # Time: </strong>5:30-7:30pm
        r'Time:([^<]+)',  # Time:5:30-7:30pm
        r'(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)\s*(?:to|-)\s*\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))',  # 5:30pm-7:30pm
        r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))',  # 7pm or 7:30pm
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return ""

def extract_location_from_text(text):
    """Extract location information from text"""
    location_patterns = [
        r'Location:\s*<\/strong>([^<]+)',  # Location: </strong>R.House, 301 West...
        r'Location:([^<]+)',  # Location:R.House, 301 West...
        r'Venue:([^<]+)',  # Venue:Some venue
        r'Address:([^<]+)',  # Address:Some address
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "Baltimore, MD"

def scrape_baltimore_events(html_content=None, url="https://baltimoresistercities.org/events/"):
    print("Scraping Sister Cities")
    """Scrape events from Baltimore Sister Cities events page"""
    if html_content is None and url:
        response = requests.get(url)
        html_content = response.text
    
    soup = BeautifulSoup(html_content, 'html.parser')
    events = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Find all h2 headings (these contain dates)
    h2_headings = soup.find_all('h2', class_='wp-block-heading')
    
    for h2 in h2_headings:
        date_text = h2.get_text().strip()
        
        # Skip non-date headings
        if not any(char.isdigit() for char in date_text) or 'Upcoming' in date_text:
            continue
        
        # Look for the next h3 heading (event title)
        next_element = h2.find_next_sibling()
        event_name = ""
        
        # Find event name (usually in next h3)
        while next_element and next_element.name != 'h3':
            next_element = next_element.find_next_sibling()
        
        if next_element and next_element.name == 'h3':
            event_name = next_element.get_text().strip()
        
        # Get content for this event
        content = ""
        content_element = next_element if next_element else h2
        while content_element:
            content += str(content_element)
            content_element = content_element.find_next_sibling()
            if content_element and content_element.name in ['h2', 'hr']:
                break
        
        # Parse date range
        start_date_obj, end_date_obj = parse_date_range(date_text)
        
        if start_date_obj:
            # Create ISO date strings
            start_date_iso = start_date_obj.strftime("%Y-%m-%d") + "T00:00:00-05:00"
            end_date_iso = end_date_obj.strftime("%Y-%m-%d") + "T23:59:59-05:00"
            
            # Extract time if available
            time_str = extract_time_from_text(content)
            
            # Extract location
            location = extract_location_from_text(content)
            
            # Extract description (first paragraph after h3)
            desc_soup = BeautifulSoup(content, 'html.parser')
            description = ""
            paragraphs = desc_soup.find_all('p')
            for p in paragraphs:
                if p.get_text().strip():
                    description = p.get_text().strip()[:200]
                    break
            
            # Extract image URL if available
            image_url = ""
            img_tag = desc_soup.find('img')
            if img_tag and img_tag.get('data-src'):
                image_url = img_tag['data-src']
            elif img_tag and img_tag.get('src'):
                image_url = img_tag['src']
            
            # Extract more detailed URL if available
            event_url = ""
            link_tag = desc_soup.find('a', href=True)
            if link_tag:
                event_url = link_tag['href']
            
            # Generate tags based on content
            tags = ["Community", "Cultural"]
            if "film" in event_name.lower() or "screening" in event_name.lower():
                tags.append("Film")
            if "art" in event_name.lower() or "exhibition" in event_name.lower():
                tags.append("Art")
            if "meet" in event_name.lower() or "greet" in event_name.lower():
                tags.append("Networking")
            if "concert" in event_name.lower() or "music" in event_name.lower():
                tags.append("Music")
            
            # Create event object
            event = {
                "id": str(uuid.uuid4()),
                "name": event_name if event_name else f"Event on {date_text}",
                "startDate": start_date_iso,
                "endDate": end_date_iso,
                "description": description,
                "url": event_url,
                "status": "ACTIVE",
                "location": {
                    "name": "",
                    "address": location,
                    "latitude": 39.2908816,
                    "longitude": -76.610759
                },
                "imageUrl": image_url,
                "recurring": False,
                "scrapeTime": current_time,
                "tags": tags
            }
            
            events.append(event)
    
    print(f"Got {len(events)} events")
    return events

def main():
    # You can either pass HTML content directly or a URL
    url = "https://baltimoresistercities.org/events/"
    
    try:
        # Fetch and scrape events
        events = scrape_baltimore_events(url=url)
        
        # Print as formatted JSON
        print(json.dumps(events, indent=4))
        
        # Optional: Save to file
        with open('baltimore_events_output.json', 'w') as f:
            json.dump(events, f, indent=4)
        
        print(f"\nScraped {len(events)} events.")
        
    except Exception as e:
        print(f"Error scraping events: {e}")

if __name__ == "__main__":
    main()