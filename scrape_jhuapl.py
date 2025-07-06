import requests
from bs4 import BeautifulSoup
import json
import hashlib
from datetime import datetime
import re

def generate_id(text):
    """Generate a unique ID based on the event title"""
    return hashlib.md5(text.encode()).hexdigest()[:16]

def parse_detailed_event(event_url, headers):
    """Parse detailed event page to extract complete information"""
    try:
        response = requests.get(event_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract detailed information from event page
        details = {}
        
        # Get date and time info
        calendar_current = soup.find('div', class_='event-calendar-current')
        if calendar_current:
            # Extract date
            date_element = calendar_current.find('div', class_='event-calendar-start')
            if date_element:
                details['date'] = date_element.get_text(strip=True)
            
            # Extract time
            time_element = calendar_current.find('div', class_='event-calendar-time')
            if time_element:
                # Clean up time string by removing extra whitespace and newlines
                time_text = ' '.join(time_element.get_text(strip=True).split())
                details['time'] = time_text
            
            # Extract location
            location_element = calendar_current.find('div', class_='event-calendar-location')
            if location_element:
                details['location'] = location_element.get_text(strip=True)
        
        # Extract description from event-content-description
        description_element = soup.find('div', class_='event-content-description')
        if description_element:
            # Remove the Event Categories section if it exists
            for unwanted in description_element.find_all('div', class_='filter-links-with-eyebrow'):
                unwanted.decompose()
            
            # Get all text content but clean it up
            description_text = description_element.get_text(separator='\n', strip=True)
            details['description'] = description_text
        
        # Extract categories
        categories = []
        category_section = soup.find('div', class_='filter-links-with-eyebrow')
        if category_section:
            category_links = category_section.find_all('a', class_='minor-link')
            for link in category_links:
                categories.append(link.get_text(strip=True))
        details['categories'] = categories
        
        return details
        
    except Exception as e:
        print(f"Error parsing detailed event page {event_url}: {e}")
        return {}

def parse_date_time(date_str, time_str):
    """Parse date and time strings to ISO format"""
    if not date_str or not time_str:
        return None, None
    
    # Parse date like "Thursday, July 17"
    date_pattern = r'(\w+),\s+(\w+)\s+(\d+)'
    date_match = re.search(date_pattern, date_str)
    
    if not date_match:
        return None, None
    
    day_name, month_name, day_num = date_match.groups()
    
    # Map month names to numbers
    month_map = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12'
    }
    
    month_num = month_map.get(month_name, '01')
    year = '2025'  # Assume current year
    
    # Parse time like "3:00 PM - 4:00 PM"
    time_parts = [t.strip() for t in time_str.split('-')]
    if len(time_parts) < 2:
        return None, None
    
    start_time_str = time_parts[0].strip()
    end_time_str = time_parts[1].strip()
    
    # Convert to 24-hour format
    try:
        start_time = convert_to_24hour(start_time_str)
        end_time = convert_to_24hour(end_time_str)
    except:
        return None, None
    
    # Format as ISO dates
    iso_date = f"{year}-{month_num}-{day_num.zfill(2)}"
    start_date = f"{iso_date}T{start_time}-04:00"
    end_date = f"{iso_date}T{end_time}-04:00"
    
    return start_date, end_date

def convert_to_24hour(time_str):
    """Convert time like '3:00 PM' to '15:00:00'"""
    time_obj = datetime.strptime(time_str.strip(), '%I:%M %p')
    return time_obj.strftime('%H:%M:%S')

def scrape_jhu_events():
    """Scrape JHU APL events page and return JSON format"""
    url = "https://www.jhuapl.edu/events"
    
    try:
        # Make request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all event cards
        cards = soup.find_all('div', class_='card-group--item')
        
        events = []
        
        for i, card in enumerate(cards):
            try:
                print(f"Processing event {i+1}/{len(cards)}...")
                
                # Extract basic info from card
                title_element = card.find('h3', class_='card__title')
                if not title_element:
                    continue
                    
                title_span = title_element.find('span')
                if not title_span:
                    continue
                    
                title = title_span.get_text(strip=True)
                
                # Extract URL
                link_element = card.find('a', class_='clickable-soldier')
                event_url = link_element.get('href') if link_element else ""
                if event_url and not event_url.startswith('http'):
                    event_url = "https://www.jhuapl.edu" + event_url
                
                # Extract image URL from card
                img_element = card.find('img')
                image_url = ""
                if img_element:
                    image_url = img_element.get('data-src') or img_element.get('src') or ""
                
                # Get detailed information from event page
                detailed_info = {}
                if event_url:
                    print(f"  Fetching details from: {event_url}")
                    detailed_info = parse_detailed_event(event_url, headers)
                
                # Parse dates and times - skip if we can't get valid times
                start_date, end_date = parse_date_time(
                    detailed_info.get('date'), 
                    detailed_info.get('time')
                )
                
                if not start_date or not end_date:
                    print(f"  Skipping event due to missing/invalid date/time")
                    continue
                
                # Create event object
                event = {
                    "id": generate_id(title),
                    "name": title,
                    "startDate": start_date,
                    "endTime": end_date,
                    "description": detailed_info.get('description', ''),
                    "url": event_url,
                    "status": "ACTIVE",
                    "location": {
                        "name": detailed_info.get('location', 'Location TBD'),
                        "address": detailed_info.get('location', 'Location TBD')
                    },
                    "imageUrl": image_url,
                    "recurring": False,
                    "categories": detailed_info.get('categories', []),
                    "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                }
                
                events.append(event)
                
            except Exception as e:
                print(f"Error processing card: {e}")
                continue
        
        return events
        
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return []
    except Exception as e:
        print(f"Error parsing page: {e}")
        return []

def main():
    """Main function to run the scraper"""
    print("Scraping JHU APL events...")
    events = scrape_jhu_events()
    
    if events:
        print(f"Found {len(events)} events")
        
        # Save to JSON file
        with open('jhu_events.json', 'w') as f:
            json.dump(events, f, indent=2)
        
        # Print first event as example
        if events:
            print("\nFirst event:")
            print(json.dumps(events[0], indent=2))
    else:
        print("No events found")

if __name__ == "__main__":
    main()