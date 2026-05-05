from bs4 import BeautifulSoup
import json
import hashlib
from datetime import datetime, timezone
import pytz
import re
from http_client import build_session, polite_get

def generate_event_id(name, start_date):
    """Generate a unique event ID based on name and start date"""
    combined = f"{name}{start_date}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]

def parse_datetime(datetime_text):
    """Parse datetime string into ISO format"""
    try:
        print(f"Parsing datetime: '{datetime_text}'")  # Debug output
        
        if not datetime_text:
            return None, None
            
        # Handle format: "August 5 @ 6:00 pm – 8:00 pm"
        # Split by @ to separate date and time
        if '@' in datetime_text:
            date_part, time_part = datetime_text.split('@', 1)
            date_part = date_part.strip()
            time_part = time_part.strip()
        else:
            # Fallback: try to extract date from the beginning
            parts = datetime_text.split()
            if len(parts) >= 2:
                date_part = f"{parts[0]} {parts[1]}"  # e.g., "August 5"
                time_part = ' '.join(parts[2:]) if len(parts) > 2 else ""
            else:
                return None, None
        
        # Add current year to date if not present
        current_year = datetime.now().year
        if str(current_year) not in date_part:
            date_part = f"{date_part}, {current_year}"
        
        # Parse time part to get start and end times
        start_time = None
        end_time = None
        
        if time_part:
            # Handle different separators for time ranges
            time_separators = ['–', '-', ' - ', ' to ']
            time_range = None
            
            for sep in time_separators:
                if sep in time_part:
                    time_range = time_part.split(sep)
                    break
            
            if time_range and len(time_range) >= 2:
                start_time = time_range[0].strip()
                end_time = time_range[1].strip()
            else:
                start_time = time_part.strip()
        
        # Parse start datetime
        if start_time:
            full_start = f"{date_part} {start_time}"
            try:
                # Try common formats
                for fmt in ["%B %d, %Y %I:%M %p", "%B %d, %Y %H:%M"]:
                    try:
                        dt_start = datetime.strptime(full_start, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format worked, try just the date
                    dt_start = datetime.strptime(date_part, "%B %d, %Y")
                    dt_start = dt_start.replace(hour=18)  # Default to 6 PM
            except ValueError as e:
                print(f"Error parsing start time '{full_start}': {e}")
                return None, None
            
            # Make datetime timezone-aware
            eastern = pytz.timezone('America/New_York')
            dt_start = eastern.localize(dt_start)
            start_iso = dt_start.isoformat()
            
            # Parse end datetime
            if end_time:
                full_end = f"{date_part} {end_time}"
                try:
                    for fmt in ["%B %d, %Y %I:%M %p", "%B %d, %Y %H:%M"]:
                        try:
                            dt_end = datetime.strptime(full_end, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        # Fallback to start time + 2 hours
                        dt_end = dt_start.replace(hour=dt_start.hour + 2)
                except ValueError:
                    dt_end = dt_start.replace(hour=dt_start.hour + 2)  # Default 2 hour duration
                
                dt_end = eastern.localize(dt_end)
                end_iso = dt_end.isoformat()
            else:
                # Default to 2 hours after start
                dt_end = dt_start.replace(hour=dt_start.hour + 2)
                dt_end = eastern.localize(dt_end)
                end_iso = dt_end.isoformat()
            
            return start_iso, end_iso
    
    except Exception as e:
        print(f"Error parsing datetime '{datetime_text}': {e}")
    
    return None, None

def scrape_baltimore_indie_games():
    """Scrape events from Baltimore Indie Games website"""
    url = "https://baltimoreindiegames.com/events/"
    
    try:
        session = build_session()
        # Send GET request
        response = polite_get(session, url, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        
        # Find all event rows
        event_rows = soup.find_all('div', class_='tribe-events-calendar-list__event-row')
        
        for row in event_rows:
            try:
                # Extract event details
                event_wrapper = row.find('div', class_='tribe-events-calendar-list__event-wrapper')
                if not event_wrapper:
                    continue
                    
                article = event_wrapper.find('article', class_='tribe-events-calendar-list__event')
                if not article:
                    continue
                
                # Extract title and URL
                title_link = article.find('a', class_='tribe-events-calendar-list__event-title-link')
                if not title_link:
                    continue
                    
                name = title_link.get_text(strip=True)
                event_url = title_link.get('href', '')
                
                # Extract datetime - get the full datetime text
                datetime_elem = article.find('time', class_='tribe-events-calendar-list__event-datetime')
                if datetime_elem:
                    # Get the full datetime text including both date and time
                    full_datetime = datetime_elem.get_text(strip=True)
                    start_date, end_time = parse_datetime(full_datetime)
                else:
                    start_date, end_time = None, None
                
                # Extract venue information
                venue_elem = article.find('address', class_='tribe-events-calendar-list__event-venue')
                venue_name = ""
                venue_address = ""
                
                if venue_elem:
                    venue_title_elem = venue_elem.find('span', class_='tribe-events-calendar-list__event-venue-title')
                    venue_address_elem = venue_elem.find('span', class_='tribe-events-calendar-list__event-venue-address')
                    
                    venue_name = venue_title_elem.get_text(strip=True) if venue_title_elem else ""
                    venue_address = venue_address_elem.get_text(strip=True) if venue_address_elem else ""
                
                # Extract description
                desc_elem = article.find('div', class_='tribe-events-calendar-list__event-description')
                description = ""
                if desc_elem:
                    # Get the paragraph content
                    p_elem = desc_elem.find('p')
                    if p_elem:
                        description = p_elem.get_text(strip=True)
                
                # Generate event ID
                event_id = generate_event_id(name, start_date or "")
                
                # Create event object
                event = {
                    "id": event_id,
                    "name": name,
                    "startDate": start_date,
                    "endTime": end_time,
                    "description": description,
                    "url": event_url,
                    "status": "ACTIVE",
                    "location": {
                        "name": venue_address if venue_address else venue_name,
                        "address": venue_address if venue_address else venue_name
                    },
                    "imageUrl": "https://baltimoreindiegames.com/wp-content/uploads/2025/03/BIG_small.png",
                    "recurring": False,  # Assume non-recurring unless specified
                    "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                }
                
                events.append(event)
                print(f"Scraped event: {name}")
                
            except Exception as e:
                print(f"Error processing event: {e}")
                continue
        
        return events
        
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return []
    except Exception as e:
        print(f"Error parsing the webpage: {e}")
        return []

def main():
    """Main function to scrape events and output JSON"""
    print("Scraping Baltimore Indie Games events...")
    
    events = scrape_baltimore_indie_games()
    
    if events:
        # Output as JSON
        json_output = json.dumps(events, indent=2)
        print("\n" + "="*50)
        print("SCRAPED EVENTS (JSON FORMAT)")
        print("="*50)
        print(json_output)
        
        
        print(f"\nSuccessfully scraped {len(events)} events!")
        print("Events saved to 'baltimore_indie_games_events.json'")
    else:
        print("No events found or error occurred during scraping.")
    return events
if __name__ == "__main__":
    # Optionally save to file
    with open('baltimore_indie_games_events.json', 'w') as f:
        f.write(json.dumps(scrape_baltimore_indie_games(),indent=2))
