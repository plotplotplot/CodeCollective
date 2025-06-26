import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import urllib.parse

def parse_date(date_str, year=2025):
    """Parse various date formats and return ISO format with default times"""
    
    # Handle specific dates like "Thursday, June 26, 5–7 p.m."
    specific_date_pattern = r'(\w+day),?\s+(\w+)\s+(\d+),?\s+(\d+)–(\d+)\s+p\.m\.'
    match = re.search(specific_date_pattern, date_str)
    if match:
        day_name, month_name, day, start_hour, end_hour = match.groups()
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        month = month_map.get(month_name, 6)  # Default to June if not found
        start_time = f"{year}-{month:02d}-{int(day):02d}T{int(start_hour) + 12}:00:00-0400"
        end_time = f"{year}-{month:02d}-{int(day):02d}T{int(end_hour) + 12}:00:00-0400"
        return start_time, end_time
    
    # Handle month-year format like "September 2025"
    month_year_pattern = r'(\w+)\s+(\d{4})'
    match = re.search(month_year_pattern, date_str)
    if match:
        month_name, year_str = match.groups()
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        month = month_map.get(month_name, 6)
        # Use middle of month (15th)
        start_time = f"{year_str}-{month:02d}-15T12:00:00-0400"
        end_time = f"{year_str}-{month:02d}-15T17:00:00-0400"
        return start_time, end_time
    
    # Handle seasons like "Fall 2025"
    season_pattern = r'(\w+)\s+(\d{4})'
    match = re.search(season_pattern, date_str)
    if match:
        season, year_str = match.groups()
        season_map = {
            'Spring': ('03', '15'),  # March 15
            'Summer': ('06', '15'),  # June 15
            'Fall': ('09', '15'),    # September 15
            'Winter': ('12', '15')   # December 15
        }
        month, day = season_map.get(season, ('06', '15'))
        start_time = f"{year_str}-{month}-{day}T12:00:00-0400"
        end_time = f"{year_str}-{month}-{day}T17:00:00-0400"
        return start_time, end_time
    
    # Default fallback
    start_time = f"{year}-06-15T12:00:00-0400"
    end_time = f"{year}-06-15T17:00:00-0400"
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
                
                # Split description to separate date and description
                parts = desc_text.split(':', 1)
                if len(parts) == 2:
                    date_part = parts[0].strip()
                    description = parts[1].strip()
                else:
                    date_part = desc_text
                    description = desc_text
                
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
                        "address": "Towson, MD"
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