"""
Scraper for Maryland Forward Party events
https://www.marylandforwardparty.com/get-involved
"""

import requests
import re
from datetime import datetime
from typing import List, Dict, Optional


def fetch_page(url: str) -> Optional[str]:
    """Fetch webpage content"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def parse_iso_datetime(iso_string: str) -> str:
    """Parse ISO datetime string and convert to expected format with timezone"""
    try:
        # Handle ISO format like "2026-03-23T23:00:00.000Z"
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        # Convert to Eastern Time (rough approximation with -04:00)
        return dt.strftime("%Y-%m-%dT%H:%M:%S-04:00")
    except ValueError:
        # Try other formats like "May 06, 2026, 12:10 PM"
        try:
            dt = datetime.strptime(iso_string, "%B %d, %Y, %I:%M %p")
            return dt.strftime("%Y-%m-%dT%H:%M:%S-04:00")
        except ValueError:
            try:
                dt = datetime.strptime(iso_string, "%b %d, %Y, %I:%M %p")
                return dt.strftime("%Y-%m-%dT%H:%M:%S-04:00")
            except Exception:
                pass
        # If all parsing fails, return as-is
        return iso_string
    except Exception:
        return iso_string


def extract_events(html: str) -> List[Dict]:
    """Extract events from the HTML page"""
    events = []
    
    # Find all scheduling sections to locate event data
    scheduling_matches = list(re.finditer(r'"scheduling":\{', html))
    
    for match in scheduling_matches:
        # Extract context around the scheduling section
        context_start = max(0, match.start() - 800)
        context_end = min(len(html), match.end() + 1000)
        context = html[context_start:context_end]
        
        # Extract event fields
        title_match = re.search(r'"title":"([^"]+)"', context)
        start_date_match = re.search(r'"startDate":"([^"]+)"', context)
        end_date_match = re.search(r'"endDate":"([^"]+)"', context)
        slug_match = re.search(r'"slug":"([^"]+)"', context)
        tz_match = re.search(r'"timeZoneId":"([^"]+)"', context)
        desc_match = re.search(r'"description":"([^"]*)"[,}]', context)
        
        if title_match and start_date_match and end_date_match:
            title = title_match.group(1)
            start_date = start_date_match.group(1)
            end_date = end_date_match.group(1)
            slug = slug_match.group(1) if slug_match else None
            description = desc_match.group(1) if desc_match else ""
            
            # Clean up escaped characters in description
            description = description.replace('\\/', '/').replace('\\n', ' ').replace('\\t', ' ').replace('\\r', '')
            description = description.strip()
            
            # Build event URL
            event_url = f"https://www.marylandforwardparty.com/events/{slug}" if slug else "https://www.marylandforwardparty.com/events"
            
            event = {
                "name": title,
                "startDate": parse_iso_datetime(start_date),
                "endTime": parse_iso_datetime(end_date),
                "description": description,
                "url": event_url,
                "status": "ACTIVE",
                "location": {
                    "name": "Maryland Forward Party Event",
                    "address": "Maryland"
                },
            }
            
            events.append(event)
    
    # Remove duplicates based on name and start date
    seen = set()
    unique_events = []
    for event in events:
        key = (event.get('name', ''), event.get('startDate', ''))
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
    
    return unique_events


def scrape_events() -> List[Dict]:
    """
    Main scraping function for Maryland Forward Party events
    
    Returns:
        List of event dictionaries in the standardized format
    """
    url = "https://www.marylandforwardparty.com/events"
    
    print(f"Fetching Maryland Forward Party events from {url}")
    html = fetch_page(url)
    
    if not html:
        print("Failed to fetch page")
        return []
    
    events = extract_events(html)
    print(f"Extracted {len(events)} unique events")
    
    return events


if __name__ == "__main__":
    events = scrape_events()
    
    # Print events for debugging
    print(f"\nFound {len(events)} events:")
    print("=" * 60)
    for i, event in enumerate(events, 1):
        print(f"{i}. {event['name']}")
        print(f"   Date: {event['startDate']}")
        print(f"   URL: {event['url']}")
        if event.get('description'):
            print(f"   Description: {event['description'][:100]}...")
        print("-" * 60)
    
    # Save to file for testing
    import json
    output_file = 'maryland_forward_party_events.json'
    with open(output_file, 'w') as f:
        json.dump(events, f, indent=2)
    print(f"\nSaved to {output_file}")
