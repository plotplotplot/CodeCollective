import requests
from bs4 import BeautifulSoup
from datetime import datetime
import uuid
import json
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

BASE_URL = "https://www.tedcomd.com"
REQUEST_TIMEOUT = 10
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_REQUESTS = 0.5


def make_request(url: str, attempt: int = 1) -> Optional[requests.Response]:
    """Make HTTP request with retry logic and error handling."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        if attempt < RETRY_ATTEMPTS:
            print(f"Request failed (attempt {attempt}/{RETRY_ATTEMPTS}): {e}")
            time.sleep(DELAY_BETWEEN_REQUESTS * attempt)
            return make_request(url, attempt + 1)
        else:
            print(f"Failed to fetch {url} after {RETRY_ATTEMPTS} attempts: {e}")
            return None


def parse_time(time_str: str) -> str:
    """Parse time string like '08:00 AM' to HH:MM format."""
    try:
        time_str = time_str.strip()
        if not time_str:
            return ""
        # Handle formats like "08:00 AM" or "8:00 PM"
        dt = datetime.strptime(time_str, "%I:%M %p")
        return dt.strftime("%H:%M")
    except ValueError:
        return time_str


def parse_event_page(url: str) -> Dict[str, Optional[str]]:
    """Scrape an individual event page for details."""
    response = make_request(url)
    if not response:
        return {
            "description": "",
            "image_url": None,
            "location_name": None,
            "address": None,
            "end_date": None
        }
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Get description
    desc_elem = soup.select_one(".field--name-body")
    description = desc_elem.get_text(strip=True, separator=" ") if desc_elem else ""
    
    # Get image
    img_elem = soup.select_one("article img")
    image_url = None
    if img_elem and img_elem.get("src"):
        src = img_elem["src"]
        image_url = urljoin(BASE_URL, src) if not src.startswith("http") else src
    
    # Try to find location information
    location_name = None
    address = None
    
    # Look for location field
    loc_field = soup.select_one(".field--name-field-location")
    if loc_field:
        location_name = loc_field.get_text(strip=True)
    
    # Look for address field
    addr_field = soup.select_one(".field--name-field-address")
    if addr_field:
        address = addr_field.get_text(strip=True)
    
    # Try to find end date if different from start
    end_date = None
    date_field = soup.select_one(".field--name-field-calendar-date")
    if date_field:
        date_text = date_field.get_text()
        # Look for date ranges
        if " to " in date_text or " - " in date_text:
            parts = re.split(r" to | - ", date_text)
            if len(parts) == 2:
                try:
                    end_date = datetime.strptime(parts[1].strip(), "%B %d, %Y").isoformat()
                except ValueError:
                    pass
    
    return {
        "description": description,
        "image_url": image_url,
        "location_name": location_name,
        "address": address,
        "end_date": end_date
    }


def extract_events_from_calendar(soup: BeautifulSoup) -> List[Dict]:
    """Extract events from the calendar table."""
    events = []
    
    # Find all calendar cells that contain events
    event_cells = soup.select("td.single-day")
    
    for cell in event_cells:
        date_str = cell.get("data-date")
        if not date_str:
            continue
        
        # Find all event items in this cell
        event_items = cell.select(".view-item")
        
        for item in event_items:
            # Get event link and name
            link = item.select_one("a")
            if not link:
                continue
            
            name = link.get_text(strip=True)
            event_url = link.get("href", "")
            if not event_url.startswith("http"):
                event_url = urljoin(BASE_URL, event_url)
            
            # Get time if available
            contents_div = item.select_one(".contents")
            time_str = ""
            if contents_div:
                text = contents_div.get_text(strip=True)
                # Extract time (appears after the link text)
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text)
                if time_match:
                    time_str = parse_time(time_match.group(1))
            
            # Create ISO datetime
            start_datetime = None
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if time_str:
                        # Combine date with time
                        time_obj = datetime.strptime(time_str, "%H:%M")
                        date_obj = date_obj.replace(hour=time_obj.hour, minute=time_obj.minute)
                    start_datetime = date_obj.isoformat()
                except ValueError as e:
                    print(f"Date parsing error for {date_str}: {e}")
            
            events.append({
                "name": name,
                "url": event_url,
                "start_date": start_datetime,
                "date_str": date_str
            })
    
    return events


def get_next_month_url(soup: BeautifulSoup) -> Optional[str]:
    """Find the 'next month' link."""
    next_link = soup.select_one(".calendar-pager__item--next a")
    if next_link and next_link.get("href"):
        href = next_link["href"]
        return urljoin(BASE_URL, href)
    return None


def scrape_tedco_events(months: int = 2) -> List[Dict]:
    """
    Scrape TEDCO events calendar.
    
    Args:
        months: Number of months to scrape (default: 2)
    
    Returns:
        List of event dictionaries
    """
    all_events = []
    visited_urls = set()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Start with current month
    current_url = f"{BASE_URL}/events"
    
    for month_num in range(months):
        if not current_url or current_url in visited_urls:
            break
        
        print(f"Scraping month {month_num + 1}/{months}: {current_url}")
        visited_urls.add(current_url)
        
        response = make_request(current_url)
        if not response:
            print(f"Failed to fetch {current_url}")
            break
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract events from calendar
        events = extract_events_from_calendar(soup)
        print(f"Found {len(events)} events")
        
        # Get detailed information for each event
        for idx, ev in enumerate(events, 1):
            print(f"  Processing event {idx}/{len(events)}: {ev['name']}")
            
            # Fetch event details
            details = parse_event_page(ev["url"])
            time.sleep(DELAY_BETWEEN_REQUESTS)  # Be polite
            
            all_events.append({
                "id": uuid.uuid4().hex,
                "name": ev["name"],
                "startDate": ev["start_date"] or "",
                "endDate": details["end_date"] or "",
                "description": details["description"],
                "url": ev["url"],
                "status": "ACTIVE",
                "location": {
                    "name": details["location_name"] or "",
                    "address": details["address"] or ""
                },
                "imageUrl": details["image_url"] or "",
                "recurring": False,
                "scrapeTime": now
            })
        
        # Get next month URL
        current_url = get_next_month_url(soup)
        if current_url:
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    return all_events


def save_events_to_json(events: List[Dict], filename: str = "tedco_events.json"):
    """Save events to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(events)} events to {filename}")


if __name__ == "__main__":
    print("Starting TEDCO event scraper...")
    print("-" * 50)
    
    events = scrape_tedco_events(months=2)
    
    print("-" * 50)
    print(f"\nTotal events scraped: {len(events)}")
    
    # Save to file
    save_events_to_json(events)
    
    # Print summary
    if events:
        print("\nSample event:")
        print(json.dumps(events[0], indent=2))
    else:
        print("\nNo events found!")