import requests
import json
import sys
from datetime import datetime

def get_all_events_from_supabase():
    """
    Retrieve all events from the Supabase metamap_config_data table without filtering
    """
    api_url = "https://wzdzsrtbclynkjaaliiz.supabase.co/rest/v1/metamap_config_data"
    
    headers = {
        "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind6ZHpzcnRiY2x5bmtqYWFsaWl6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODY2Njg5MjQsImV4cCI6MjAwMjI0NDkyNH0.eUuGV31DkZogU6z-ljLpSjLbyceC2cmrG2_-0x0TfwM",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind6ZHpzcnRiY2x5bmtqYWFsaWl6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODY2Njg5MjQsImV4cCI6MjAwMjI0NDkyNH0.eUuGV31DkZogU6z-ljLpSjLbyceC2cmrG2_-0x0TfwM"
    }
    
    # Get all records without filtering
    query_url = f"{api_url}?select=*"
    
    try:
        # Make the GET request
        response = requests.get(query_url, headers=headers)
        response.raise_for_status()
        
        # Parse the response to JSON
        data = response.json()
        
        print(f"Retrieved {len(data)} configuration records")
        return data
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching events from Supabase: {e}")
        return []

def get_baltimore_events():
    """
    Get events from Baltimore.tech platform
    This function is separate from the Supabase call to show a more complete picture
    """
    api_url = "https://baltimore.tech/api/1.1/obj/Event"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        events = data.get('response', {}).get('results', [])
        
        print(f"Retrieved {len(events)} events from Baltimore.tech API")
        
        # Format the events to match our desired structure
        formatted_events = []
        for event in events:
            # Extract event details
            event_id = event.get('_id', '')
            
            # Format location data
            location = {
                "name": event.get('Location_Name', ''),
                "address": event.get('Address', ''),
                "city": event.get('City', ''),
                "state": event.get('State', ''),
                "country": event.get('Country', 'US')
            }
            
            # Format the event in our desired structure
            formatted_event = {
                "id": event_id,
                "name": event.get('Name', ''),
                "description": event.get('Description', ''),
                "startDate": event.get('Date'),
                "endTime": event.get('End_Date'),
                "url": f"https://baltimore.tech/event-profile/{event_id}",
                "status": "ACTIVE",
                "location": location,
                "imageUrl": event.get('Image', '')
            }
            
            formatted_events.append(formatted_event)
        
        return formatted_events
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching events from Baltimore.tech: {e}")
        return []

def load_sample_events(sample_file="paste-2.txt"):
    """Load sample event data from file"""
    try:
        with open(sample_file, 'r') as f:
            content = f.read()
            events = json.loads(content)
        print(f"Loaded {len(events)} sample events")
        return events
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading sample events: {e}")
        return []

def combine_events(baltimore_events, sample_events):
    """
    Combine events from Baltimore.tech API and sample data
    Removes duplicates based on event ID
    """
    # Create a dictionary to track events by ID
    events_dict = {}
    
    # Add Baltimore events
    for event in baltimore_events:
        event_id = event.get('id')
        if event_id:
            events_dict[event_id] = event
    
    # Add sample events (will overwrite if duplicate ID)
    for event in sample_events:
        event_id = event.get('id')
        if event_id:
            events_dict[event_id] = event
    
    # Convert back to list
    combined_events = list(events_dict.values())
    
    print(f"Combined into {len(combined_events)} unique events")
    return combined_events

def main():
    # Get all configuration records from Supabase
    supabase_data = get_all_events_from_supabase()
    
    # Print URLs from Supabase data
    print("\nURLs from Supabase:")
    for idx, item in enumerate(supabase_data):
        url = item.get('url', 'No URL')
        print(f"{idx+1}. {url}")
    
    # Try to get events from Baltimore.tech API
    baltimore_events = get_baltimore_events()
    
    # Load sample events
    sample_events = load_sample_events()
    
    # Combine events from both sources
    all_events = combine_events(baltimore_events, sample_events)
    
    # Save to file if requested
    if "--save" in sys.argv:
        output_file = "all_events.json"
        with open(output_file, 'w') as f:
            json.dump(all_events, f, indent=4)
        print(f"\nSaved {len(all_events)} events to {output_file}")
    
    # Print events as JSON
    print("\nAll Events:")
    print(json.dumps(all_events, indent=4))
    
    return all_events

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Events Retrieval Script")
        print("Usage:")
        print("  python get_events.py         - Get all events")
        print("  python get_events.py --save  - Get all events and save to all_events.json")
    else:
        main()