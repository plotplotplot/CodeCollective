import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

def scrape_google_form(url):
    """
    Scrape Google Form and extract event information
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract basic information
        title = soup.find('title')
        title_text = title.text.strip() if title else "Unknown Event"
        
        # Extract description from meta tags
        description_meta = soup.find('meta', {'property': 'og:description'}) or soup.find('meta', {'name': 'description'})
        description = description_meta.get('content', '') if description_meta else ''
        
        # Extract form ID from URL
        form_id_match = re.search(r'/forms/d/e/([^/]+)/', url)
        form_id = form_id_match.group(1) if form_id_match else None
        
        # Parse event details from description
        event_info = parse_event_details(description, title_text)
        
        # Create event object in the requested format
        event = {
            "id": form_id or generate_id_from_url(url),
            "name": title_text,
            "description": description,
            "startDate": event_info.get('start_date'),
            "endTime": event_info.get('end_time'),
            "url": url,
            "status": "ACTIVE",
            "location": event_info.get('location', {}),
            "imageUrl": extract_image_url(soup),
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }
        
        return [event]  # Return as list to match the requested format
        
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []
    except Exception as e:
        print(f"Error processing content: {e}")
        return []

def parse_event_details(description, title):
    """
    Parse event details from description text
    """
    event_info = {
        'start_date': None,
        'end_time': None,
        'location': {}
    }
    
    print(f"DEBUG: Parsing description: {description[:500]}...")  # Debug output
    
    # Extract date information - looking for "Friday, August 1, 2025"
    date_patterns = [
        r'Date:\s*([^\n]+)',  # "Date: Friday, August 1, 2025"
        r'(\w+,\s*\w+\s+\d+,\s*\d{4})',  # "Friday, August 1, 2025"
        r'(\w+\s+\d+,\s*\d{4})',  # "August 1, 2025"
        r'(\d{1,2}/\d{1,2}/\d{4})'  # "8/1/2025"
    ]
    
    date_found = None
    for pattern in date_patterns:
        date_match = re.search(pattern, description, re.IGNORECASE | re.MULTILINE)
        if date_match:
            date_str = date_match.group(1).strip()
            print(f"DEBUG: Found date string: '{date_str}'")
            
            # Try to parse common date formats
            date_formats = [
                '%A, %B %d, %Y',  # "Friday, August 1, 2025"
                '%B %d, %Y',      # "August 1, 2025"
                '%m/%d/%Y',       # "8/1/2025"
                '%d/%m/%Y'        # "1/8/2025"
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    date_found = parsed_date
                    print(f"DEBUG: Successfully parsed date: {parsed_date}")
                    break
                except ValueError as e:
                    print(f"DEBUG: Failed to parse '{date_str}' with format '{fmt}': {e}")
                    continue
            
            if date_found:
                break
    
    # Extract time information - looking for "9:00 AM – 12:00 PM"
    time_patterns = [
        r'Time:\s*([^\n]+)',  # "Time: 9:00 AM – 12:00 PM"
        r'(\d{1,2}:\d{2}\s*[AP]M\s*[–-]\s*\d{1,2}:\d{2}\s*[AP]M)',  # "9:00 AM – 12:00 PM"
        r'(\d{1,2}:\d{2}\s*[AP]M)'  # Single time
    ]
    
    start_time = None
    end_time = None
    
    for pattern in time_patterns:
        time_match = re.search(pattern, description, re.IGNORECASE | re.MULTILINE)
        if time_match:
            time_str = time_match.group(1).strip()
            print(f"DEBUG: Found time string: '{time_str}'")
            
            # For time ranges like "9:00 AM – 12:00 PM"
            if '–' in time_str or '-' in time_str:
                # Split on em dash or regular dash
                times = re.split('[–-]', time_str)
                if len(times) >= 2:
                    start_time_str = times[0].strip()
                    end_time_str = times[1].strip()
                    
                    # Parse start time
                    start_time = parse_time_string(start_time_str)
                    end_time = parse_time_string(end_time_str)
                    
                    print(f"DEBUG: Parsed start time: {start_time}, end time: {end_time}")
            else:
                start_time = parse_time_string(time_str)
                print(f"DEBUG: Parsed single time: {start_time}")
            break
    
    # Combine date and time
    if date_found and start_time:
        start_datetime = datetime.combine(date_found.date(), start_time)
        event_info['start_date'] = start_datetime.strftime("%Y-%m-%dT%H:%M:%S-04:00")
        print(f"DEBUG: Combined start datetime: {event_info['start_date']}")
    
    if date_found and end_time:
        end_datetime = datetime.combine(date_found.date(), end_time)
        event_info['end_time'] = end_datetime.strftime("%Y-%m-%dT%H:%M:%S-04:00")
        print(f"DEBUG: Combined end datetime: {event_info['end_time']}")
    
    # Extract location information - looking for "81 Mosher Street, Baltimore, MD 21217"
    location_patterns = [
        r'Location:\s*([^\n]+)',  # "Location: 81 Mosher Street, Baltimore, MD 21217"
        r'(\d+\s+[^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)[^,\n]*(?:,\s*[^,\n]+)*)'
    ]
    
    for pattern in location_patterns:
        location_match = re.search(pattern, description, re.IGNORECASE | re.MULTILINE)
        if location_match:
            location_str = location_match.group(1).strip()
            print(f"DEBUG: Found location string: '{location_str}'")
            event_info['location'] = parse_location(location_str)
            break
    
    return event_info

def parse_time_string(time_str):
    """
    Parse time string like "9:00 AM" or "12:00 PM" into time object
    """
    time_formats = [
        '%I:%M %p',  # "9:00 AM"
        '%H:%M',     # "09:00"
        '%I %p',     # "9 AM"
    ]
    
    for fmt in time_formats:
        try:
            time_obj = datetime.strptime(time_str.strip(), fmt)
            return time_obj.time()
        except ValueError:
            continue
    
    print(f"DEBUG: Could not parse time string: '{time_str}'")
    return None

def parse_location(location_str):
    """
    Parse location string into structured format
    """
    location = {
        "name": "",
        "address": "",
        "city": "",
        "state": "",
        "country": "us"
    }
    
    print(f"DEBUG: Parsing location: '{location_str}'")
    
    # Split by commas and try to parse
    parts = [part.strip() for part in location_str.split(',')]
    print(f"DEBUG: Location parts: {parts}")
    
    if len(parts) >= 1:
        # First part is likely the address (e.g., "81 Mosher Street")
        if any(word in parts[0].lower() for word in ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'boulevard', 'blvd']):
            location['address'] = parts[0]
        else:
            # If no street indicator, treat as name
            location['name'] = parts[0]
    
    if len(parts) >= 2:
        # Second part could be city (e.g., "Baltimore")
        location['city'] = parts[1]
    
    if len(parts) >= 3:
        # Third part might be "MD 21217" or just "MD"
        state_zip = parts[2].strip()
        
        # Try to extract state and zip
        state_zip_pattern = r'^([A-Z]{2})\s*(\d{5})?'
        match = re.match(state_zip_pattern, state_zip)
        if match:
            location['state'] = match.group(1)
        else:
            # Fallback - assume it's just state
            if len(state_zip) <= 3:
                location['state'] = state_zip
    
    print(f"DEBUG: Parsed location: {location}")
    return location

def extract_image_url(soup):
    """
    Extract image URL from page
    """
    # Try meta tags first
    img_meta = soup.find('meta', {'property': 'og:image'}) or soup.find('meta', {'name': 'image'})
    if img_meta and img_meta.get('content'):
        return img_meta['content']
    
    # Try to find images in the content
    images = soup.find_all('img')
    for img in images:
        src = img.get('src')
        if src and not src.startswith('data:'):
            return src
    
    return "/event_images/google_form_event.webp"  # Default placeholder

def generate_id_from_url(url):
    """
    Generate a unique ID from URL
    """
    import hashlib
    return str(abs(hash(url)) % (10 ** 9))

def scrape(url = "http://docs.google.com/forms/d/e/1FAIpQLSfAHwexta7vxLto1xmvBxFNawicAUtRrjTKqN0jHs25RjLCQg/viewform"):
    """
    Main function to scrape the Google Form
    """
    
    
    # Convert http to https for security
    if url.startswith('http://'):
        url = url.replace('http://', 'https://')
    
    print(f"Scraping: {url}")
    return scrape_google_form(url)
    
def main():
    events = scrape()

    if events:
        # Output as JSON
        print(json.dumps(events, indent=2, ensure_ascii=False))
        
        # Optionally save to file
        with open('google_form_events.json', 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        
        print(f"\nSuccessfully scraped {len(events)} event(s)")
        print("Results saved to 'google_form_events.json'")
    else:
        print("No events found or error occurred")

if __name__ == "__main__":
    main()