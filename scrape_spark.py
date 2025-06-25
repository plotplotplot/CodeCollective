import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from urllib.parse import urljoin

def scrape_spark_events(url="https://sparkcoworking.com/baltimore/"):
    """
    Scrape events from Spark Coworking Baltimore website and return in specified format
    """
    try:
        # Get the webpage content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all event modals
        event_modals = soup.find_all('div', class_='modal fade event-modal')
        
        events = []
        
        for modal in event_modals:
            try:
                event_data = parse_event_modal(modal, url)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                print(f"Error parsing event modal: {e}")
                continue
        
        return events
    
    except requests.RequestException as e:
        print(f"Error fetching webpage: {e}")
        return []
    except Exception as e:
        print(f"Error parsing webpage: {e}")
        return []

def parse_event_modal(modal, base_url):
    """
    Parse individual event modal and extract event information
    """
    event = {}
    
    # Extract event name from modal title
    title_element = modal.find('h3', class_='modal-title')
    if title_element:
        event['name'] = title_element.get_text(strip=True)
    else:
        return None
    
    # Extract modal body content
    modal_body = modal.find('div', class_='modal-body')
    if not modal_body:
        return None
    
    # Extract date and time
    date_time_info = extract_date_time(modal_body)
    if date_time_info:
        event.update(date_time_info)
    
    # Extract description
    description_parts = []
    paragraphs = modal_body.find_all('p')
    for p in paragraphs:
        text = p.get_text(strip=True)
        if text and not text.startswith('About the Speaker:') and not text.startswith('Spark Flex is proud'):
            description_parts.append(text)
    
    event['description'] = ' '.join(description_parts)
    
    # Extract ticket URL
    ticket_link = modal_body.find('a', class_='btn')
    if ticket_link and ticket_link.get('href'):
        event['url'] = ticket_link['href']
    else:
        event['url'] = base_url
    
    # Extract location
    location_info = extract_location(modal_body)
    event['location'] = location_info
    
    # Set default values
    event['imageUrl'] = "https://sparkcoworking.com/baltimore/wp-content/uploads/sites/6/2018/05/spark-baltimore-logo.png"  # No image URL available in the modal
    event['status'] = "ACTIVE"
    
    return event

def extract_date_time(modal_body):
    """
    Extract date and time information from modal body
    """
    date_time_info = {}
    
    # Look for date and time in h6 elements
    h6_elements = modal_body.find_all('h6')
    
    date_text = None
    time_text = None
    
    for h6 in h6_elements:
        text = h6.get_text(strip=True)
        
        # Check if it's a date (contains day of week and date)
        if any(day in text for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
            date_text = text
        # Check if it's a time (contains time pattern)
        elif re.search(r'\d{1,2}:\d{2}', text):
            time_text = text
    
    if date_text and time_text:
        # Parse date and time
        try:
            # Extract date components
            date_match = re.search(r'(\w+),\s*(\w+)\s*(\d+)', date_text)
            if date_match:
                day_name, month_name, day = date_match.groups()
                
                # Extract time components
                time_match = re.search(r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)', time_text.lower())
                if time_match:
                    start_hour, start_min, end_hour, end_min, period = time_match.groups()
                    
                    # Convert to 24-hour format
                    start_hour = int(start_hour)
                    end_hour = int(end_hour)
                    
                    if period == 'pm' and start_hour < 12:
                        start_hour += 12
                    if period == 'pm' and end_hour < 12:
                        end_hour += 12
                    
                    # Create datetime strings (assuming current year)
                    current_year = datetime.now().year
                    month_num = datetime.strptime(month_name, '%B').month
                    
                    start_datetime = f"{current_year}-{month_num:02d}-{int(day):02d}T{start_hour:02d}:{start_min}:00-0400"
                    end_datetime = f"{current_year}-{month_num:02d}-{int(day):02d}T{end_hour:02d}:{end_min}:00-0400"
                    
                    date_time_info['startDate'] = start_datetime
                    date_time_info['endTime'] = end_datetime
                    
        except Exception as e:
            print(f"Error parsing date/time: {e}")
    
    return date_time_info

def extract_location(modal_body):
    """
    Extract location information from modal body
    """
    location = {
        "name": "Spark Flex",
        "address": "Baltimore, MD"
    }
    
    # Look for location in h6 elements
    h6_elements = modal_body.find_all('h6')
    for h6 in h6_elements:
        text = h6.get_text(strip=True)
        if text.startswith('Location:'):
            location_name = text.replace('Location:', '').strip()
            location['name'] = location_name
            break
    
    return location

def main():
    """
    Main function to scrape events and print results
    """
    print("Scraping events from Spark Coworking Baltimore...")
    events = scrape_spark_events()
    
    if events:
        print(f"Found {len(events)} events:")
        print(json.dumps(events, indent=2))
    else:
        print("No events found or error occurred during scraping.")
    
    return events

if __name__ == "__main__":
    # Required packages (install with pip):
    # pip install requests beautifulsoup4
    
    events = main()