import json
import re
import uuid
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from http_client import build_session, polite_get

def extract_meridiem(time_str):
    match = re.search(r'\b([ap])\s*\.?\s*m\.?\b', time_str, re.IGNORECASE)
    if not match:
        return None
    return f"{match.group(1).lower()}m"


def parse_time_to_hour_minute(time_str):
    """Convert time string like '7pm', '7:30pm', '5:30-7:30pm' to hour and minute"""
    if not time_str:
        return None, None, None, None  # start_hour, start_minute, end_hour, end_minute
    
    # Clean the time string - remove timezone indicators
    time_str = time_str.lower().strip()
    time_str = re.sub(r'\s*(?:et|est|edt|eastern\s*time)\b', '', time_str)
    
    # Handle time ranges
    if '-' in time_str or '–' in time_str or 'to' in time_str:
        # Replace different separators
        time_str = time_str.replace('–', '-').replace('to', '-')
        parts = time_str.split('-')
        if len(parts) >= 2:
            start_time = parts[0].strip()
            end_time = parts[1].strip()

            # If only one side has AM/PM, apply it to the other side.
            start_meridiem = extract_meridiem(start_time)
            end_meridiem = extract_meridiem(end_time)
            start_has_meridiem = start_meridiem is not None
            end_has_meridiem = end_meridiem is not None
            if not start_has_meridiem and not end_has_meridiem:
                start_time = f"{start_time}pm"
                end_time = f"{end_time}pm"
            elif start_has_meridiem and not end_has_meridiem:
                end_time = f"{end_time}{start_meridiem}"
            elif end_has_meridiem and not start_has_meridiem:
                start_time = f"{start_time}{end_meridiem}"
            
            # Parse start time
            start_hour, start_minute = parse_single_time(start_time)
            
            # Parse end time
            end_hour, end_minute = parse_single_time(end_time)
            
            return start_hour, start_minute, end_hour, end_minute
    else:
        # Single time
        hour, minute = parse_single_time(time_str)
        return hour, minute, hour, minute  # Same start and end
    
    return None, None, None, None

def parse_single_time(time_str):
    """Parse single time string like '7pm', '7:30pm', '1pm'"""
    time_str = time_str.strip().lower()
    
    # Remove am/pm indicators and spaces
    meridiem = extract_meridiem(time_str)
    is_pm = meridiem == "pm"
    time_str = re.sub(r'\b[ap]\s*\.?\s*m\.?\b', '', time_str).strip()
    
    # Extract numbers only (remove any non-numeric characters after digits)
    match = re.search(r'(\d{1,2})(?::(\d{2}))?', time_str)
    if not match:
        return None, None
    
    hour_str = match.group(1)
    minute_str = match.group(2)
    
    hour = int(hour_str)
    minute = int(minute_str) if minute_str else 0
    
    # Convert to 24-hour format if PM
    if is_pm and hour < 12:
        hour += 12
    elif not is_pm and hour == 12:  # 12am
        hour = 0
    
    return hour, minute

def parse_date_range(date_string):
    """Parse date range strings like 'September 21, 2025 – March 8, 2025' or 'January 22, 2026'"""
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
            "%m/%d/%Y",   # 09/21/2025
            "%d %B, %Y"   # 22 January, 2026
        ]
        
        for date_format in date_formats:
            try:
                date = datetime.strptime(date_string, date_format)
                return date, date
            except ValueError:
                continue
    
    return None, None

def extract_time_from_text(text):
    """Extract time information from text - improved version"""
    # Look for Time in media-text content first (more structured)
    media_text_divs = re.findall(r'<div[^>]*class="wp-block-media-text__content"[^>]*>.*?</div>', text, re.DOTALL)
    
    for media_text in media_text_divs:
        # Multiple patterns to catch different formats
        patterns = [
            r'Time:\s*</?strong>?\s*([^<]+)',  # Time: </strong>5:30-7:30pm
            r'<strong>Time:\s*</strong>\s*([^<]+)',  # <strong>Time:</strong> 5:30-7:30pm
            r'Time:\s*([^<\n]+)',  # Time:5:30-7:30pm
        ]
        
        for pattern in patterns:
            time_match = re.search(pattern, media_text, re.IGNORECASE)
            if time_match:
                time_str = time_match.group(1).strip()
                # Clean up any extra HTML tags
                time_str = re.sub(r'<[^>]+>', '', time_str)
                # Remove any trailing punctuation
                time_str = re.sub(r'[.,;:]$', '', time_str)
                return time_str
    
    # Fallback to general text search
    time_patterns = [
        r'Time:\s*</?strong>?\s*([^<\n]+)',  # Time: </strong>5:30-7:30pm
        r'<strong>Time:\s*</strong>\s*([^<\n]+)',  # <strong>Time:</strong> 5:30-7:30pm
        r'Time:\s*([^<\n]+)',  # Time:5:30-7:30pm
        r'(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)\s*(?:to|-|–)\s*\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))',  # 5:30pm-7:30pm
        r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))',  # 7pm or 7:30pm
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            time_str = match.group(1).strip()
            # Clean up any extra HTML tags
            time_str = re.sub(r'<[^>]+>', '', time_str)
            # Remove any trailing punctuation
            time_str = re.sub(r'[.,;:]$', '', time_str)
            return time_str
    
    return ""

def extract_location_from_text(text):
    """Extract location information from text"""
    # Look for Location in media-text content first
    media_text_divs = re.findall(r'<div[^>]*class="wp-block-media-text__content"[^>]*>.*?</div>', text, re.DOTALL)
    
    for media_text in media_text_divs:
        # Multiple patterns to catch different formats
        patterns = [
            r'Location:\s*</?strong>?\s*([^<]+)',  # Location: </strong>R.House...
            r'<strong>Location:\s*</strong>\s*([^<]+)',  # <strong>Location:</strong> R.House...
            r'Location:\s*([^<\n]+)',  # Location:R.House...
        ]
        
        for pattern in patterns:
            loc_match = re.search(pattern, media_text, re.IGNORECASE)
            if loc_match:
                loc_str = loc_match.group(1).strip()
                # Clean up any extra HTML tags
                loc_str = re.sub(r'<[^>]+>', '', loc_str)
                # Remove any trailing punctuation
                loc_str = re.sub(r'[.,;:]$', '', loc_str)
                return loc_str
    
    # Fallback to general text search
    location_patterns = [
        r'Location:\s*</?strong>?\s*([^<\n]+)',  # Location: </strong>R.House, 301 West...
        r'<strong>Location:\s*</strong>\s*([^<\n]+)',  # <strong>Location:</strong> R.House...
        r'Location:\s*([^<\n]+)',  # Location:R.House, 301 West...
        r'Venue:\s*([^<\n]+)',  # Venue:Some venue
        r'Address:\s*([^<\n]+)',  # Address:Some address
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            loc_str = match.group(1).strip()
            # Clean up any extra HTML tags
            loc_str = re.sub(r'<[^>]+>', '', loc_str)
            # Remove any trailing punctuation
            loc_str = re.sub(r'[.,;:]$', '', loc_str)
            return loc_str
    
    return "Baltimore, MD"

def create_iso_datetime(date_obj, hour=None, minute=None):
    """Create ISO datetime string with optional time"""
    if hour is not None and minute is not None:
        # Create datetime with specific time
        datetime_obj = datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S-05:00")
    elif hour is not None:
        # Only hour specified
        datetime_obj = datetime(date_obj.year, date_obj.month, date_obj.day, hour, 0)
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S-05:00")
    else:
        # Use default time (start of day for startDate, end of day for endDate)
        if minute is None:
            # Default to start of day
            return date_obj.strftime("%Y-%m-%dT00:00:00-05:00")
        else:
            # Handle case where we only have minute (unlikely)
            return date_obj.strftime("%Y-%m-%dT00:%M:00-05:00")

def scrape_baltimore_events(html_content=None, url="https://baltimoresistercities.org/events/"):
    print("Scraping Sister Cities")
    """Scrape events from Baltimore Sister Cities events page"""
    if html_content is None and url:
        session = build_session()
        response = polite_get(session, url, timeout=30)
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
            # Extract time if available
            time_str = extract_time_from_text(content)
            
            # Parse time to get hours and minutes
            start_hour, start_minute, end_hour, end_minute = parse_time_to_hour_minute(time_str)
            
            # Calculate duration in days
            duration_days = (end_date_obj - start_date_obj).days
            
            # Check if event is more than 3 days long
            if duration_days > 3:
                # Modify event name to add "Start"
                event_name = f"{event_name} Start"
                
                # Make it a 2-hour event at the beginning
                if start_hour is not None:
                    # Use specified start time
                    start_date_iso = create_iso_datetime(start_date_obj, start_hour, start_minute or 0)
                    # Add 2 hours to start time
                    end_datetime = datetime(start_date_obj.year, start_date_obj.month, start_date_obj.day, 
                                           start_hour, start_minute or 0) + timedelta(hours=2)
                    end_date_iso = end_datetime.strftime("%Y-%m-%dT%H:%M:%S-05:00")
                else:
                    # Default to 10am-12pm if no time specified
                    start_date_iso = create_iso_datetime(start_date_obj, 10, 0)
                    end_date_iso = create_iso_datetime(start_date_obj, 12, 0)
                
                print(f"Event: {event_name}")
                print(f"Duration: {duration_days} days (converted to 2-hour event)")
                print(f"Start: {start_date_iso}, End: {end_date_iso}")
            else:
                # Normal event handling (3 days or less)
                # Debug logging
                if time_str:
                    print(f"Event: {event_name}")
                    print(f"Time string: '{time_str}'")
                    print(f"Parsed times: start={start_hour}:{start_minute}, end={end_hour}:{end_minute}")
                
                # Create ISO date strings with times
                if start_hour is not None:
                    start_date_iso = create_iso_datetime(start_date_obj, start_hour, start_minute or 0)
                    
                    # If end time is not specified, make it 2 hours after start time
                    if end_hour is None or (end_hour == start_hour and end_minute == start_minute):
                        # Add 2 hours to start time
                        end_datetime = datetime(start_date_obj.year, start_date_obj.month, start_date_obj.day, 
                                               start_hour, start_minute or 0) + timedelta(hours=2)
                        end_date_iso = end_datetime.strftime("%Y-%m-%dT%H:%M:%S-05:00")
                    else:
                        # Use specified end time
                        end_date_iso = create_iso_datetime(end_date_obj, end_hour, end_minute or 0)
                else:
                    # Default to 10am-12pm if no time specified
                    start_date_iso = create_iso_datetime(start_date_obj, 10, 0)
                    end_date_iso = create_iso_datetime(start_date_obj, 12, 0)
            
            # Extract location
            location = extract_location_from_text(content)
            
            # Extract description (get all paragraphs, not just first one)
            desc_soup = BeautifulSoup(content, 'html.parser')
            description_parts = []
            
            # Get text from paragraphs, excluding media-text content which has time/location
            for element in desc_soup.find_all(['p', 'div']):
                class_attr = element.get('class', [])
                class_str = ' '.join(class_attr) if class_attr else ''
                if 'wp-block-media-text__content' not in class_str:
                    text = element.get_text().strip()
                    if text and not any(keyword in text.lower() for keyword in ['time:', 'location:', 'admission:', 'more information:', 'click here', 'register', 'rsvp']):
                        description_parts.append(text)
            
            description = ' '.join(description_parts)[:200] if description_parts else ""
            
            # Extract image URL if available
            image_url = ""
            img_tag = desc_soup.find('img')
            if img_tag:
                if img_tag.get('data-src'):
                    image_url = img_tag['data-src']
                elif img_tag.get('src'):
                    image_url = img_tag['src']
            
            # Extract more detailed URL if available
            event_url = ""
            link_tags = desc_soup.find_all('a', href=True)
            for link in link_tags:
                href = link['href']
                # Prefer external event URLs over internal ones
                if 'creativealliance' in href or 'artbma' in href or 'wallergallery' in href:
                    event_url = href
                    break
                elif href and not href.startswith('#') and 'baltimoresistercities.org' not in href:
                    event_url = href
                    break
            if not event_url and link_tags:
                # Fallback to first link
                event_url = link_tags[0]['href']
            
            # Generate tags based on content
            tags = ["Community", "Cultural"]
            if "film" in event_name.lower() or "screening" in event_name.lower():
                tags.append("Film")
            if "art" in event_name.lower() or "exhibition" in event_name.lower():
                tags.append("Art")
            if "meet" in event_name.lower() or "greet" in event_name.lower():
                tags.append("Networking")
                tags.append("Social")
            if "concert" in event_name.lower() or "music" in event_name.lower():
                tags.append("Music")
                tags.append("Performance")
            if "summit" in event_name.lower() or "conference" in event_name.lower():
                tags.append("Conference")
            if "immigration" in event_name.lower():
                tags.append("Immigration")
            
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
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
