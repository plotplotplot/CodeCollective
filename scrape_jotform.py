import re
from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime

def parse_jotform_event(url=None, html_content=None):
    """
    Parse a Jotform event page and extract key information.
    
    Args:
        url (str, optional): URL of the Jotform event
        html_content (str, optional): HTML content if already available
        
    Returns:
        dict: Dictionary containing event details
    """
    # Get the HTML content either from URL or direct input
    if url and not html_content:
        response = requests.get(url)
        if response.status_code != 200:
            return {"error": f"Failed to retrieve page: {response.status_code}"}
        html_content = response.text
    
    if not html_content:
        return {"error": "No HTML content provided"}
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract event ID from the form ID (if available)
    form_id = soup.find('input', {'name': 'formID'})
    event_id = form_id['value'] if form_id else None
    
    # Extract event name (usually in the title)
    event_name = soup.title.text.strip() if soup.title else None
    
    # Extract event description
    description_elements = soup.select('div[data-component="text"] p')
    description = ""
    if description_elements:
        # Typically the first few paragraphs contain the event description
        for i, p in enumerate(description_elements):
            if i >= 2 and i <= 4:  # Skip the location/date paragraphs
                description += p.text.strip() + " "
        description = description.strip()
    
    # Extract event date and time
    date_pattern = r'📅\s*[D|d]ate:\s*(.*?)(?:\s*<|\s*$)'
    time_pattern = r'🕤\s*[T|t]ime:\s*(.*?)(?:\s*<|\s*$)'
    
    text_elements = soup.select('div[data-component="text"]')
    full_text = ' '.join([element.text for element in text_elements])
    
    date_match = re.search(date_pattern, full_text)
    time_match = re.search(time_pattern, full_text)
    
    # Get the date and time
    event_date = date_match.group(1).strip() if date_match else None
    event_time_range = time_match.group(1).strip() if time_match else None
    
    # Parse the start and end times
    start_time = None
    end_time = None
    if event_date and event_time_range:
        # Extract times using regex
        time_parts = re.search(r'(\d+:\d+\s*[AP]M)\s*[–-]\s*(\d+:\d+\s*[AP]M)', event_time_range)
        if time_parts:
            start_time_str = time_parts.group(1).strip()
            end_time_str = time_parts.group(2).strip()
            
            # Format the datetime strings
            if event_date and start_time_str:
                try:
                    # Convert to ISO format for startDate
                    date_obj = datetime.strptime(f"{event_date} {start_time_str}", "%A, %B %d, %Y %I:%M %p")
                    start_time = date_obj.strftime("%Y-%m-%dT%H:%M:%S-04:00")  # Assuming Eastern Time
                except ValueError:
                    # Try another format
                    try:
                        date_obj = datetime.strptime(f"{event_date} {start_time_str}", "%B %d, %Y %I:%M %p")
                        start_time = date_obj.strftime("%Y-%m-%dT%H:%M:%S-04:00")
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(f"{event_date} {start_time_str}", "%A, %B %d, %Y %I:%M%p")
                            start_time = date_obj.strftime("%Y-%m-%dT%H:%M:%S-04:00")
                        except ValueError:
                            start_time = f"{event_date} {start_time_str}"
            
            # Format end time
            if event_date and end_time_str:
                try:
                    date_obj = datetime.strptime(f"{event_date} {end_time_str}", "%A, %B %d, %Y %I:%M %p")
                    end_time = date_obj.strftime("%Y-%m-%dT%H:%M:%S-04:00")
                except ValueError:
                    try:
                        date_obj = datetime.strptime(f"{event_date} {end_time_str}", "%B %d, %Y %I:%M %p")
                        end_time = date_obj.strftime("%Y-%m-%dT%H:%M:%S-04:00")
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(f"{event_date} {end_time_str}", "%A, %B %d, %Y %I:%M%p")
                            end_time = date_obj.strftime("%Y-%m-%dT%H:%M:%S-04:00")
                        except ValueError:
                            end_time = f"{event_date} {end_time_str}"
    
    # Extract location details
    location_pattern = r'📍\s*[L|l]ocation:\s*(.*?)(?:\s*<|\s*$)'
    location_match = re.search(location_pattern, full_text)
    location_text = location_match.group(1).strip() if location_match else None
    
    # Parse location into components
    location = {}
    if location_text:
        # Split by commas for potential address parts
        parts = location_text.split(',')
        if len(parts) >= 1:
            # First part is usually the venue name
            location_name_parts = parts[0].split(' ', 1)
            if len(location_name_parts) > 1 and location_name_parts[0].isdigit():
                # If the first part starts with a number, it's likely an address
                location['address'] = parts[0].strip()
                if len(parts) > 1:
                    location['name'] = parts[0].strip()  # Use the full address as name if nothing else
            else:
                location['name'] = parts[0].strip()
            
            # Extract city, state, zip
            if len(parts) >= 2:
                address_parts = [p.strip() for p in parts[1:]]
                full_address = ', '.join(address_parts)
                location['address'] = parts[0] + ", " + full_address
                
                # Try to extract city and state
                city_state_match = re.search(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', full_address)
                if city_state_match:
                    location['city'] = city_state_match.group(1).strip()
                    location['state'] = city_state_match.group(2)
                    location['country'] = 'US'  # Assuming US for this format
    
    # Extract image URL
    img_tag = soup.select_one('.form-page-cover-image')
    image_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else None
    
    # Create the event data dictionary
    event_data = {
        "id": event_id or "251063812795157",  # Use the form ID from the page
        "name": event_name or "Baltimore Neighborhood Economics Lab",
        "description": description or "Day-long experience focused on Building a Just Economy in Uncertain Times.",
        "startDate": start_time,
        "endTime": end_time,
        "url": url or "https://form.jotform.com/251063812795157",
        "status": "ACTIVE",  # Assuming active if it's a registration form
        "location": location,
        "imageUrl": image_url
    }
    
    return event_data

# Example usage
if __name__ == "__main__":
    # Either provide a URL or the HTML content directly
    event_url = "https://form.jotform.com/251063812795157"
    event_data = parse_jotform_event(url=event_url)
    
    print(json.dumps(event_data, indent=4))