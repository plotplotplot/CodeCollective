#!/usr/bin/env python3
"""
Universal Eventbrite Events Scraper
Extracts upcoming events from any Eventbrite organizer page
"""

import re
import json
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventbriteScraper:
    """Scraper for Eventbrite organizer pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def scrape_events(self, url: str) -> List[Dict[str, Any]]:
        """
        Main method to scrape events from an Eventbrite organizer page
        
        Args:
            url (str): Eventbrite organizer page URL
            
        Returns:
            List[Dict]: List of formatted event dictionaries
        """
        try:
            html_content = self._fetch_page(url)
            return self._parse_events_from_html(html_content)
        except Exception as e:
            logger.error(f"Failed to scrape events from {url}: {str(e)}")
            raise
    
    def _fetch_page(self, url: str) -> str:
        """Fetch HTML content from URL"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch page: {str(e)}")
    
    def _parse_events_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse events from HTML content"""
        # Extract __SERVER_DATA__ using regex
        server_data_match = re.search(
            r'window\.__SERVER_DATA__\s*=\s*({.*?});',
            html_content,
            re.DOTALL
        )
        
        if not server_data_match:
            raise Exception("Could not find __SERVER_DATA__ in HTML content - this may not be an Eventbrite organizer page")
        
        try:
            server_data = json.loads(server_data_match.group(1))
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse __SERVER_DATA__ JSON: {str(e)}")
        
        return self._extract_events_from_server_data(server_data)
    
    def _extract_events_from_server_data(self, server_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from server data"""
        jsonld_data = server_data.get('jsonld', [])
        if not isinstance(jsonld_data, list):
            raise Exception("No JSON-LD data found in server data")
        
        # Find the ItemList containing events
        item_list_data = None
        for item in jsonld_data:
            if (item.get('@context') == 'https://schema.org' and 
                'itemListElement' in item and 
                isinstance(item['itemListElement'], list)):
                item_list_data = item
                break
        
        if not item_list_data or not item_list_data.get('itemListElement'):
            logger.warning("No event list found - organizer may have no upcoming events")
            return []
        
        events = []
        current_time = datetime.now(timezone.utc)
        
        # Process each event
        for list_item in item_list_data['itemListElement']:
            event_data = list_item.get('item', {})
            if event_data.get('@type') != 'Event':
                continue
            
            try:
                # Parse dates
                start_date_str = event_data.get('startDate')
                end_date_str = event_data.get('endDate')
                
                if not start_date_str or not end_date_str:
                    logger.warning(f"Event {event_data.get('name', 'Unknown')} missing date information")
                    continue
                
                end_date = self._parse_datetime(end_date_str)
                
                # Only include upcoming events (events that haven't ended yet)
                if end_date > current_time:
                    formatted_event = self._format_event(event_data)
                    if formatted_event:
                        events.append(formatted_event)
                        
            except Exception as e:
                logger.warning(f"Error processing event {event_data.get('name', 'Unknown')}: {str(e)}")
                continue
        
        # Sort events by start date
        events.sort(key=lambda x: self._parse_datetime(x['startDate']))
        
        logger.info(f"Found {len(events)} upcoming events")
        return events
    
    def _format_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format a single event into the required structure"""
        try:
            location = self._format_location(event_data.get('location', {}))
            image_url = event_data.get('image')
            
            return {
                'name': event_data.get('name', 'Unknown Event'),
                'description': event_data.get('description') or event_data.get('name', 'Unknown Event'),
                'startDate': event_data.get('startDate'),
                'endTime': event_data.get('endDate'),
                'url': event_data.get('url'),
                'status': 'ACTIVE',
                'location': location,
                'imageUrl': image_url
            }
        except Exception as e:
            logger.warning(f"Failed to format event {event_data.get('name', 'Unknown')}: {str(e)}")
            return None
    
    def _format_location(self, location_data: Dict[str, Any]) -> Dict[str, str]:
        """Format location information"""
        if not location_data:
            return {
                'name': 'Unknown Location',
                'address': 'Unknown Address'
            }
        
        return {
            'name': location_data.get('name', 'Unknown Location'),
            'address': self._format_address(location_data.get('address', {}))
        }
    
    def _format_address(self, address: Dict[str, Any]) -> str:
        """Format address from structured data"""
        if not address:
            return 'Unknown Address'
        
        parts = []
        for field in ['streetAddress', 'addressLocality', 'addressRegion', 'postalCode']:
            if address.get(field):
                parts.append(address[field])
        
        return ', '.join(parts) if parts else 'Unknown Address'
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string with timezone support"""
        if not datetime_str:
            raise ValueError("Empty datetime string")
        
        # Handle different timezone formats
        # Convert -0400 format to -04:00 format for Python compatibility
        if datetime_str.endswith(('-0400', '-0500', '-0600', '-0700', '-0800', '-0900')):
            # Insert colon in timezone offset
            datetime_str = datetime_str[:-2] + ':' + datetime_str[-2:]
        elif datetime_str.endswith(('+0400', '+0500', '+0600', '+0700', '+0800', '+0900')):
            # Insert colon in timezone offset for positive offsets
            datetime_str = datetime_str[:-2] + ':' + datetime_str[-2:]
        elif datetime_str.endswith('Z'):
            # Replace Z with +00:00
            datetime_str = datetime_str[:-1] + '+00:00'
        
        try:
            return datetime.fromisoformat(datetime_str)
        except ValueError as e:
            # If fromisoformat still fails, try using strptime as fallback
            import re
            from dateutil import parser
            try:
                return parser.parse(datetime_str)
            except ImportError:
                # If dateutil is not available, use manual parsing
                return self._manual_datetime_parse(datetime_str)
    
    def _manual_datetime_parse(self, datetime_str: str) -> datetime:
        """Manual datetime parsing as fallback"""
        import re
        
        # Pattern to match ISO datetime with timezone
        pattern = r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}):?(\d{2})'
        match = re.match(pattern, datetime_str)
        
        if not match:
            raise ValueError(f"Cannot parse datetime: {datetime_str}")
        
        year, month, day, hour, minute, second, tz_sign_hour, tz_minute = match.groups()
        
        # Create timezone offset
        tz_offset_minutes = int(tz_sign_hour) * 60 + int(tz_minute)
        if tz_sign_hour.startswith('-'):
            tz_offset_minutes = -abs(tz_offset_minutes)
        
        tz_offset = timezone(timedelta(minutes=tz_offset_minutes))
        
        return datetime(
            int(year), int(month), int(day),
            int(hour), int(minute), int(second),
            tzinfo=tz_offset
        )
    
    def get_organizer_info(self, server_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get organizer information from the page"""
        jsonld_data = server_data.get('jsonld', [])
        if not isinstance(jsonld_data, list):
            return None
        
        for item in jsonld_data:
            if (item.get('@type') == 'ProfilePage' and 
                item.get('mainEntity', {}).get('@type') == 'Organization'):
                main_entity = item['mainEntity']
                return {
                    'name': main_entity.get('name'),
                    'socialLinks': main_entity.get('sameAs', []),
                    'logo': main_entity.get('logo', {}).get('url')
                }
        
        return None


def scrape_eventbrite_organizer(url: str) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape events from an Eventbrite organizer page
    
    Args:
        url (str): Eventbrite organizer page URL
        
    Returns:
        List[Dict]: List of formatted event dictionaries
    """
    scraper = EventbriteScraper()
    
    try:
        logger.info(f"Scraping events from: {url}")
        events = scraper.scrape_events(url)
        
        logger.info(f"Found {len(events)} upcoming events:")
        for i, event in enumerate(events, 1):
            logger.info(f"{i}. {event['name']}")
            logger.info(f"   Date: {event['startDate']}")
            logger.info(f"   Location: {event['location']['name']}")
            logger.info(f"   URL: {event['url']}")
        
        return events
        
    except Exception as e:
        logger.error(f"Error scraping events: {str(e)}")
        return []


def save_events_to_json(events: List[Dict[str, Any]], filename: str = 'events.json') -> None:
    """Save events to a JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        logger.info(f"Events saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save events to {filename}: {str(e)}")


def main():
    """Example usage"""
    # Example URLs
    example_urls = [
        'https://www.eventbrite.com/o/baltimore-under-ground-science-space-bugss-4318633291',
        'https://www.eventbrite.com.au/o/it-social-baltimore-110781946041'
    ]
    
    all_events = []
    
    for url in example_urls:
        try:
            events = scrape_eventbrite_organizer(url)
            all_events.extend(events)
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {str(e)}")
    
    if all_events:
        # Save all events to JSON file
        save_events_to_json(all_events)
        
        # Print sample event
        print("\nSample event:")
        print(json.dumps(all_events[0], indent=2) if all_events else "No events found")


if __name__ == "__main__":
    main()