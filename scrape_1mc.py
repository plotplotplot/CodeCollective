from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import hashlib
import json
from http_client import build_session, polite_get

BASE_URL = "https://www.1millioncups.com"
EVENTS_PATH = "/s/events?community=baltimore"
SCRAPE_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

def make_id(name, start):
    hash_input = f"{name}_{start}"
    return hashlib.sha1(hash_input.encode()).hexdigest()[:16]

def parse_event_time(text):
    """
    Attempts to parse event datetime like 'Wednesday, Sep 25, 2025 9:00 AM - 10:00 AM'
    """
    try:
        # Extract just the first datetime from the string
        parts = text.split('-')[0].strip()
        return datetime.strptime(parts, "%A, %b %d, %Y %I:%M %p")
    except ValueError:
        return None

def scrape():
    session = build_session()
    response = polite_get(session, BASE_URL + EVENTS_PATH, timeout=20)
    response.raise_for_status()
    print("DEBUG - Raw HTML response length:", len(response.text))  # Debug output
    # Print first 1000 chars to inspect structure
    with open("onemc.html", 'w+') as f:
        f.write(response.text)
    print("DEBUG - HTML sample:", response.text[:1000])
    soup = BeautifulSoup(response.text, "html.parser")

    events = []

    for card in soup.select("a.event-card, a.upcoming-event"):
        title_el = card.select_one(".event-title")
        time_el = card.select_one(".event-date")
        link = BASE_URL + card.get("href", "")
        
        if not title_el or not time_el:
            continue

        name = title_el.get_text(strip=True)
        time_text = time_el.get_text(strip=True)
        start = parse_event_time(time_text)
        if not start:
            continue
        end = start + timedelta(hours=1)

        # Fetch the event detail page for description
        detail_html = polite_get(session, link, timeout=20).text
        detail_soup = BeautifulSoup(detail_html, "html.parser")
        desc_el = detail_soup.select_one(".event-description, .description")
        desc_html = desc_el.decode_contents() if desc_el else ""

        event = {
            "id": make_id(name, start.isoformat()),
            "name": name,
            "startDate": start.isoformat(),
            "endTime": end.isoformat(),
            "description": desc_html,
            "url": link,
            "status": "ACTIVE",
            "location": {
                "name": "",
                "address": ""
            },
            "imageUrl": "",
            "recurring": False,
            "scrapeTime": SCRAPE_TIME
        }
        events.append(event)

    return events

if __name__ == "__main__":
    all_events = scrape()
    print(json.dumps(all_events, indent=4))
