import requests
import json
from datetime import datetime
import hashlib

def generate_event_id(event_name, start_date):
    """Generate a unique ID based on event name and start date"""
    combined = f"{event_name}{start_date}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]

def convert_luma_to_event_format(luma_data):
    """Convert Luma API response to the desired event format"""
    events = []
    
    for entry in luma_data.get('entries', []):
        event = entry.get('event', {})
        
        # Extract basic event info
        event_id = generate_event_id(event.get('name', ''), event.get('start_at', ''))
        name = event.get('name', '')
        start_at = event.get('start_at', '')
        end_at = event.get('end_at', '')
        
        # Convert ISO timestamps to the desired format
        start_date = start_at if start_at else None
        end_time = end_at if end_at else None
        
        # Extract location info
        geo_info = event.get('geo_address_info', {})
        location_name = geo_info.get('address', '') or geo_info.get('full_address', '')
        location_address = geo_info.get('full_address', '') or location_name
        
        # Handle virtual events
        if event.get('location_type') == 'online' or event.get('virtual_info', {}).get('has_access'):
            location_name = "Virtual Event"
            location_address = "Virtual Event"
        
        # Get event URL
        event_url = f"https://lu.ma/{event.get('url', '')}" if event.get('url') else ""
        
        # Extract image URL
        image_url = event.get('cover_url', '')
        
        # Build the converted event
        converted_event = {
            "id": event_id,
            "name": name,
            "startDate": start_date,
            "endTime": end_time,
            "description": "",  # Luma API doesn't seem to include description in this endpoint
            "url": event_url,
            "status": "ACTIVE",
            "location": {
                "name": location_name,
                "address": location_address
            },
            "imageUrl": image_url,
            "recurring": False,  # Would need additional logic to determine this
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }
        
        events.append(converted_event)
    
    return events

def fetch_and_convert_luma_events(user_api_id= "usr-tYdFPQYBiZY4T6B"):
    """Main function to fetch from Luma API and convert the data"""
    
    # API endpoint
    url = "https://api.lu.ma/user/profile/events-hosting"
    params = {
        "pagination_limit": 10,
        "period": "future",
        "user_api_id": user_api_id
    }
    
    try:
        # Make the API request
        print("Fetching data from Luma API...")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Parse JSON response
        luma_data = response.json()
        print(f"Successfully fetched {len(luma_data.get('entries', []))} events")
        
        # Convert to desired format
        converted_events = convert_luma_to_event_format(luma_data)
        
        # Pretty print the converted data
        print("\nConverted events:")
        print(json.dumps(converted_events, indent=4))
        
        return converted_events
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
import sys
if __name__ == "__main__":
    events = fetch_and_convert_luma_events(sys.argv[1])
    print(json.dumps(events, indent=2))