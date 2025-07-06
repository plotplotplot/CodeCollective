import requests
from bs4 import BeautifulSoup
import json
import hashlib
from datetime import datetime
import re

def generate_id(text):
    """Generate a unique ID based on the event title"""
    return hashlib.md5(text.encode()).hexdigest()[:16]

def parse_date_range(date_string):
    """Parse date strings like 'Thursday, July 17' or 'Monday, September 08 - Friday, September 12'"""
    # Clean up the date string
    date_string = date_string.strip()
    
    # Handle date ranges
    if ' - ' in date_string:
        start_part, end_part = date_string.split(' - ', 1)
        # For now, just use the start date
        date_string = start_part.strip()
    
    # Extract day name and date
    # Pattern: "Thursday, July 17"
    pattern = r'(\w+),\s+(\w+)\s+(\d+)'
    match = re.search(pattern, date_string)
    
    if match:
        day_name, month_name, day_num = match.groups()
        
        # Map month names to numbers
        month_map = {
            'January': '01', 'February': '02', 'March': '03', 'April': '04',
            'May': '05', 'June': '06', 'July': '07', 'August': '08',
            'September': '09', 'October': '10', 'November': '11', 'December': '12'
        }
        
        month_num = month_map.get(month_name, '01')
        
        # Assume current year (2025)
        year = '2025'
        
        # Format as ISO date
        iso_date = f"{year}-{month_num}-{day_num.zfill(2)}"
        
        return f"{iso_date}T09:00:00-04:00"  # Default time
    
    return None

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
        
        for card in cards:
            try:
                # Extract event title
                title_element = card.find('h3', class_='card__title')
                if not title_element:
                    continue
                    
                title_span = title_element.find('span')
                if not title_span:
                    continue
                    
                title = title_span.get_text(strip=True)
                
                # Extract date
                date_element = card.find('h4', class_='card__event-date')
                start_date = None
                if date_element:
                    date_text = date_element.get_text(strip=True)
                    start_date = parse_date_range(date_text)
                
                # Extract location
                location_element = card.find('h4', class_='card__event-location')
                location_name = location_element.get_text(strip=True) if location_element else "Location TBD"
                
                # Extract description from card body
                description = ""
                body_element = card.find('div', class_='card__body')
                if body_element:
                    description = body_element.get_text(strip=True)
                
                # Extract URL
                link_element = card.find('a', class_='clickable-soldier')
                event_url = link_element.get('href') if link_element else ""
                if event_url and not event_url.startswith('http'):
                    event_url = "https://www.jhuapl.edu" + event_url
                
                # Extract image URL
                img_element = card.find('img')
                image_url = ""
                if img_element:
                    # Try data-src first (lazy loading), then src
                    image_url = img_element.get('data-src') or img_element.get('src') or ""
                
                # Create event object
                event = {
                    "id": generate_id(title),
                    "name": title,
                    "startDate": start_date,
                    "endTime": start_date,  # Using same as start for now
                    "description": description,
                    "url": event_url,
                    "status": "ACTIVE",
                    "location": {
                        "name": location_name,
                        "address": location_name
                    },
                    "imageUrl": image_url,
                    "recurring": False,
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