import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import urllib.parse

def parse_date(date_str, year=2025):
    """Parse various date formats and return ISO format with default times"""
    
    # Handle specific dates like "Thursday, September 18, 5–8 p.m."
    specific_date_pattern = r'(\w+day),?\s+(\w+)\s+(\d+),?\s+(\d+)(?::(\d+))?\s*–\s*(\d+)(?::(\d+))?\s*([ap]\.m\.)'
    match = re.search(specific_date_pattern, date_str, re.IGNORECASE)
    if match:
        day_name, month_name, day, start_hour, start_min, end_hour, end_min, am_pm = match.groups()
        
        # Set default minutes if not provided
        start_min = start_min or "00"
        end_min = end_min or "00"
        
        # Convert to 24-hour format
        start_hour = int(start_hour)
        end_hour = int(end_hour)
        
        if "p.m." in am_pm.lower() and start_hour < 12:
            start_hour += 12
        if "p.m." in am_pm.lower() and end_hour < 12:
            end_hour += 12
        if "a.m." in am_pm.lower() and start_hour == 12:
            start_hour = 0
        if "a.m." in am_pm.lower() and end_hour == 12:
            end_hour = 0
            
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        month = month_map.get(month_name, 9)  # Default to September if not found
        
        start_time = f"{year}-{month:02d}-{int(day):02d}T{start_hour:02d}:{start_min}:00-0400"
        end_time = f"{year}-{month:02d}-{int(day):02d}T{end_hour:02d}:{end_min}:00-0400"
        return start_time, end_time
    
    # Handle date ranges like "August 29–September 1"
    date_range_pattern = r'(\w+)\s+(\d+)–(\w+)\s+(\d+)'
    match = re.search(date_range_pattern, date_str)
    if match:
        start_month, start_day, end_month, end_day = match.groups()
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        start_month_num = month_map.get(start_month, 8)
        end_month_num = month_map.get(end_month, 9)
        
        start_time = f"{year}-{start_month_num:02d}-{int(start_day):02d}T00:00:00-0400"
        end_time = f"{year}-{end_month_num:02d}-{int(end_day):02d}T23:59:59-0400"
        return start_time, end_time
    
    # Handle single dates like "September 18"
    single_date_pattern = r'(\w+)\s+(\d+)'
    match = re.search(single_date_pattern, date_str)
    if match:
        month_name, day = match.groups()
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        month = month_map.get(month_name, 9)
        
        start_time = f"{year}-{month:02d}-{int(day):02d}T09:00:00-0400"
        end_time = f"{year}-{month:02d}-{int(day):02d}T17:00:00-0400"
        return start_time, end_time
    
    # Default fallback
    start_time = f"{year}-09-15T12:00:00-0400"
    end_time = f"{year}-09-15T17:00:00-0400"
    return start_time, end_time

def scrape_towson_events(url = "https://www.towson.edu/startup/about/events.html"):
    """Scrape events from Towson University StartUp events page"""
    
    try:
        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all event containers
        events = []
        event_containers = soup.find_all('div', class_='repeatable-visual')
        
        for container in event_containers:
            try:
                # Extract event details
                title_elem = container.find('h2', class_='section-title')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                
                # Extract description and date from paragraph
                desc_elem = container.find('p')
                if not desc_elem:
                    continue
                
                desc_text = desc_elem.get_text(strip=True)
                
                # Extract date part (should be the first part before the colon)
                date_part = ""
                description = desc_text
                
                # Look for the pattern with a colon separating date and description
                if ":" in desc_text:
                    colon_pos = desc_text.find(":")
                    date_part = desc_text[:colon_pos].strip()
                    description = desc_text[colon_pos+1:].strip()
                else:
                    # If no colon, try to extract date using regex
                    date_patterns = [
                        r'\w+day,?\s+\w+\s+\d+,?\s+\d+(?::\d+)?\s*–\s*\d+(?::\d+)?\s*[ap]\.m\.',
                        r'\w+\s+\d+–\w+\s+\d+',
                        r'\w+\s+\d+'
                    ]
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, desc_text)
                        if match:
                            date_part = match.group(0)
                            description = desc_text.replace(date_part, "").strip()
                            break
                
                # Parse dates
                start_date, end_date = parse_date(date_part)
                
                # Extract URL
                link_elem = container.find('a', class_='btn')
                event_url = ""
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('http'):
                        event_url = href
                    else:
                        event_url = urllib.parse.urljoin(url, href)
                
                # Extract image URL
                img_elem = container.find('img')
                image_url = ""
                if img_elem and img_elem.get('src'):
                    src = img_elem.get('src')
                    if src.startswith('http'):
                        image_url = src
                    else:
                        image_url = urllib.parse.urljoin(url, src)
                
                # Create event object
                event = {
                    "name": title,
                    "description": description,
                    "startDate": start_date,
                    "endTime": end_date,
                    "url": event_url,
                    "imageUrl": image_url,
                    "status": "ACTIVE",
                    "location": {
                        "name": "Towson University StarTUp",
                        "address": "307 Washington Avenue, Towson, MD 21204"
                    }
                }
                
                events.append(event)
                
            except Exception as e:
                print(f"Error processing event container: {e}")
                continue
        
        # Remove duplicates based on name and start date
        unique_events = []
        seen = set()
        for event in events:
            key = (event['name'], event['startDate'])
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        print(f"Error parsing the page: {e}")
        return []

def main():
    url = "https://www.towson.edu/startup/about/events.html"
    events = scrape_towson_events(url)
    
    if events:
        print("Scraped Events:")
        print(json.dumps(events, indent=2))
        
        # Save to file
        with open('towson_events.json', 'w') as f:
            json.dump(events, f, indent=2)
        print(f"\nSaved {len(events)} events to towson_events.json")
    else:
        print("No events found or error occurred")

if __name__ == "__main__":
    main()