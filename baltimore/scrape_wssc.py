import requests
import json
from datetime import datetime
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import uuid


class WSSCEventsScraper:
    def __init__(self):
        self.base_url = "https://www.wsscwater.com"
        self.ajax_endpoint = "/views/ajax"
        self.events_page = "/events"
    
    def fetch_events_page(self) -> Optional[str]:
        """Return the HTML for the main events page."""
        response = requests.get(f"{self.base_url}{self.events_page}")
        if response.status_code != 200:
            print(f"Failed to fetch events page: {response.status_code}")
            return None
        return response.text
        
    def fetch_events_data(
        self,
        year: str = "2025",
        view_dom_id: Optional[str] = None,
        page_html: Optional[str] = None,
    ) -> List[Dict]:
        """Fetch events data from WSSC Water website"""
        
        # First, get the initial page to extract the view_dom_id if needed
        if not view_dom_id:
            if not page_html:
                page_html = self.fetch_events_page()
            if not page_html:
                return []
            view_dom_id = self.extract_view_dom_id(page_html)
            if not view_dom_id:
                print("Could not extract view_dom_id from page")
                return []
        
        # Prepare the AJAX request
        ajax_url = f"{self.base_url}{self.ajax_endpoint}"
        
        # Form data for the AJAX request
        form_data = {
            'view_name': 'events_listing',
            'view_display_id': 'embed_1',
            'view_args': '',
            'view_path': '/node/37',
            'view_base_path': '',
            'view_dom_id': view_dom_id,
            'pager_element': '0',
            '_drupal_ajax': '1',
            'upcoming': '1',
            'month': 'all',
            'year': year,
        }
        
        # Send the AJAX request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f"{self.base_url}{self.events_page}"
        }
        
        response = requests.post(ajax_url, data=form_data, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to fetch AJAX data: {response.status_code}")
            return []
            
        # Parse the AJAX response
        return self.parse_ajax_response(response.json())
    
    def extract_view_dom_id(self, html_content: str) -> Optional[str]:
        """Extract the view_dom_id from the HTML page"""
        # Look for the view DOM ID in the page
        pattern = r'js-view-dom-id-([a-f0-9]+)'
        matches = re.search(pattern, html_content)
        
        if matches:
            return matches.group(1)
        return None
    
    def extract_available_years(self, html_content: str) -> List[str]:
        """Find available year filters on the events page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        years = set()
        
        for select in soup.find_all('select'):
            attrs = f"{select.get('name', '')} {select.get('id', '')}"
            if 'year' in attrs.lower():
                for option in select.find_all('option'):
                    value = (option.get('value') or option.text or '').strip()
                    if re.fullmatch(r'\d{4}', value):
                        years.add(value)
        
        # Fallback to regex search if select not found
        if not years:
            for value in re.findall(r'value="(\d{4})"', html_content):
                years.add(value)
        
        return sorted(years)
    
    def parse_ajax_response(self, ajax_data: List) -> List[Dict]:
        """Parse the AJAX response to extract events"""
        events = []
        
        # The AJAX response contains multiple commands, we need the insert command
        for item in ajax_data:
            if item.get('command') == 'insert' and item.get('method') == 'replaceWith':
                html_content = item.get('data', '')
                events = self.extract_events_from_html(html_content)
                break
        
        return events
    
    def extract_events_from_html(self, html_content: str) -> List[Dict]:
        """Extract events from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        events = []
        
        # Find all event articles
        event_articles = soup.find_all('article', class_='node--event')
        
        for article in event_articles:
            event = self.parse_event_article(article)
            if event:
                events.append(event)
        
        return events
    
    def parse_event_article(self, article) -> Optional[Dict]:
        """Parse a single event article"""
        try:
            # Extract date
            date_elem = article.find('div', class_='listing-teaser--date')
            time_elems = date_elem.find_all('time') if date_elem else []
            
            start_date = None
            end_date = None
            
            if time_elems:
                # Parse the first time as start date
                start_time_str = time_elems[0].get('datetime', '')
                if start_time_str:
                    start_date = self.parse_iso_date(start_time_str)
                
                # Parse the second time as end date if available
                if len(time_elems) > 1:
                    end_time_str = time_elems[1].get('datetime', '')
                    if end_time_str:
                        end_date = self.parse_iso_date(end_time_str)
                else:
                    # If no end time, use start time with 1 hour added
                    if start_date:
                        end_date = self.add_one_hour(start_date)
            
            # Extract title and URL
            title_elem = article.find('h3')
            link_elem = title_elem.find('a') if title_elem else None
            title = link_elem.text.strip() if link_elem else ''
            relative_url = link_elem.get('href', '') if link_elem else ''
            full_url = f"{self.base_url}{relative_url}" if relative_url else ''
            
            # Extract description
            desc_elem = article.find('div', class_='listing-teaser--description')
            description = desc_elem.text.strip() if desc_elem else ''
            
            # Extract event type
            type_elem = article.find('div', class_='field--name-field-event-type')
            event_type = type_elem.text.strip() if type_elem else ''
            
            # Generate a unique ID from the URL
            event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, full_url)) if full_url else str(uuid.uuid4())
            
            # Format the event data
            formatted_event = {
                "id": event_id,
                "name": title,
                "startDate": start_date,
                "endTime": end_date,
                "description": description,
                "url": full_url,
                "status": "ACTIVE",
                "location": {
                    "name": "WSSC Water",  # Default location
                    "address": "14501 Sweitzer Ln, Laurel, MD 20707"  # Default WSSC address
                },
                "imageUrl": "",  # Not available in the listing
                "recurring": False,  # Would need to parse from description
                "scrapeTime": datetime.now().isoformat()
            }
            
            return formatted_event
            
        except Exception as e:
            print(f"Error parsing event article: {e}")
            return None
    
    def parse_iso_date(self, date_str: str) -> str:
        """Convert date string to ISO 8601 format with timezone"""
        try:
            # Parse the UTC date string
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Convert to Eastern Time (UTC-4 or UTC-5 depending on DST)
            # For simplicity, we'll keep UTC and add timezone offset
            # You could add proper timezone conversion here
            return dt.isoformat() + '-04:00'  # Assuming Eastern Time
        except ValueError:
            return date_str
    
    def add_one_hour(self, date_str: str) -> str:
        """Add one hour to a date string"""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            dt = dt.replace(hour=dt.hour + 1)
            return dt.isoformat() + '-04:00'
        except:
            return date_str
    
    def scrape(self, year: str = "2025") -> List[Dict]:
        """Main scraping method"""
        print(f"Scraping WSSC Water events for {year}...")
        events = self.fetch_events_data(year)
        print(f"Found {len(events)} events")
        return events
    
    def scrape_all(self) -> List[Dict]:
        """Scrape events for all available years."""
        page_html = self.fetch_events_page()
        if not page_html:
            return []
        
        view_dom_id = self.extract_view_dom_id(page_html)
        if not view_dom_id:
            print("Could not extract view_dom_id from page")
            return []
        
        years = self.extract_available_years(page_html)
        if not years:
            # Default to current year if no options found
            years = [str(datetime.now().year)]
        
        all_events: List[Dict] = []
        for year in years:
            year_events = self.fetch_events_data(year=year, view_dom_id=view_dom_id, page_html=page_html)
            all_events.extend(year_events)
        
        print(f"Scraped {len(all_events)} events across {len(years)} year filters")
        return all_events
    
    def save_to_json(self, events: List[Dict], filename: str = "wssc_events.json"):
        """Save events to JSON file"""
        with open(filename, 'w') as f:
            json.dump(events, f, indent=2, default=str)
        print(f"Events saved to {filename}")


def scrape_wssc_events(year: str = "2025") -> List[Dict]:
    scraper = WSSCEventsScraper()
    return scraper.scrape(year)

def scrape_all_wssc_events() -> List[Dict]:
    scraper = WSSCEventsScraper()
    return scraper.scrape_all()

# Example usage
if __name__ == "__main__":
    print(json.dumps(scrape_all_wssc_events(), indent=2))
    