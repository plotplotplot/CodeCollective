from bs4 import BeautifulSoup
import json
import re
from http_client import build_session, polite_get

def parse_luma_event_page(url):
    session = build_session()
    response = polite_get(session, url)
    if response.status_code != 200:
        return {"error": f"Failed to retrieve page: {response.status_code}"}
    html_content = response.text
    
    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the JSON data in the script tag
    script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
    if not script_tag:
        return None
    
    try:
        data = json.loads(script_tag.string)
        event_data = data['props']['pageProps']['initialData']['data']
    except (json.JSONDecodeError, KeyError):
        return None
    
    # Extract basic event info
    event_info = {
        'name': event_data['event']['name'],
        'description': clean_description(event_data['description_mirror']['content']),
        'startDate': event_data['event']['start_at'],
        'endTime': event_data['event']['end_at'],
        'timezone': event_data['event']['timezone'],
        'visibility': event_data['event']['visibility'],
        'imageUrl': event_data['event']['cover_url'],
        'url': f"https://lu.ma/{event_data['event']['url']}",
        'calendar': {
            'name': event_data['calendar']['name'],
            'description': event_data['calendar']['description_short'],
            'avatar': event_data['calendar']['avatar_url']
        },
        'location': {
            'name': event_data['event']['geo_address_info']['address'],
            'full_address': event_data['event']['geo_address_info']['full_address']
        },
        'ticket_info': {
            'is_free': event_data['ticket_info']['is_free'],
            'spots_remaining': event_data['ticket_info']['spots_remaining'],
            'types': [{
                'name': tt['name'],
                'price': tt['cents'] / 100 if tt['cents'] else 0,
                'currency': tt['currency'],
                'description': tt['description']
            } for tt in event_data['ticket_types']]
        }
    }
    
    return event_info

def clean_description(content):
    """Convert the description content from JSON structure to plain text"""
    description = []
    
    for item in content:
        if item['type'] == 'paragraph':
            text = ''.join([t['text'] for t in item.get('content', []) if t['type'] == 'text'])
            description.append(text)
        elif item['type'] in ['bullet_list', 'ordered_list']:
            for li in item.get('content', []):
                if li['type'] == 'list_item':
                    text = ''.join([t['text'] for p in li.get('content', []) 
                                   for t in p.get('content', []) if t['type'] == 'text'])
                    description.append(f"• {text}")
    
    return '\n\n'.join(description)

# Example usage:
if __name__ == "__main__":
    from baltimore.event_sources import sources as sources
    event_data = None
    for source in sources:
        source_url = source.get("url", "") if isinstance(source, dict) else str(source)
        if "lu.ma" not in source_url and "luma.com" not in source_url:
            continue
        event_data = parse_luma_event_page(source_url)
        if event_data:
            break
    print(json.dumps(event_data, indent=2))
