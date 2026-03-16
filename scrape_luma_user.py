import requests
import json
from datetime import datetime
import hashlib

def generate_event_id(event_name, start_date):
    """Generate a unique ID based on event name and start date"""
    combined = f"{event_name}{start_date}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]

def convert_luma_to_event_format(luma_data, fallback_url=""):
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
        geo_info = event.get('geo_address_info', {}) or {}
        coordinate_info = event.get('coordinate', {}) or {}
        location_name = geo_info.get('address', '') or geo_info.get('full_address', '')
        location_address = geo_info.get('full_address', '') or location_name
        city = geo_info.get('city', '')
        state = geo_info.get('region', '')
        country = geo_info.get('country', '')
        latitude = coordinate_info.get('latitude') or event.get('geo_latitude', '')
        longitude = coordinate_info.get('longitude') or event.get('geo_longitude', '')
        
        # Handle virtual events
        if event.get('location_type') == 'online' or event.get('virtual_info', {}).get('has_access'):
            location_name = "Virtual Event"
            location_address = "Virtual Event"
            city = ""
            state = ""
            country = ""
            latitude = ""
            longitude = ""
        
        # Get event URL
        event_url = f"https://lu.ma/{event.get('url', '')}" if event.get('url') else fallback_url
        
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
                "address": location_address,
                "city": city,
                "state": state,
                "country": country,
                "latitude": latitude,
                "longitude": longitude
            },
            "imageUrl": image_url,
            "recurring": False,  # Would need additional logic to determine this
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }
        
        events.append(converted_event)
    
    return events

def fetch_and_convert_luma_events(user_api_id="usr-tYdFPQYBiZY4T6B", fallback_url=""):
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
        converted_events = convert_luma_to_event_format(luma_data, fallback_url=fallback_url)
        
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
    fallback_url = sys.argv[2] if len(sys.argv) > 2 else ""
    events = fetch_and_convert_luma_events(sys.argv[1], fallback_url=fallback_url)
    print(json.dumps(events, indent=2))
