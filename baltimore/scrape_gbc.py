import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

EASTERN_TZ = ZoneInfo("America/New_York")


def log_skip(reason, detail=""):
    if detail:
        print(f"GBC skip: {reason}: {detail}")
    else:
        print(f"GBC skip: {reason}")


def first_present_attr(tag, *attrs):
    if not tag:
        return ""
    for attr in attrs:
        value = tag.get(attr)
        if value:
            return value
    return ""

def scrape_gbc_events():
    """
    Scrapes events from GBC events list page and returns formatted JSON
    """
    url = "https://gbc.org/events/list/"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        events = []
        seen_urls = set()
        next_url = url

        while next_url:
            response = requests.get(next_url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            event_articles = soup.find_all('article', class_='tribe-events-calendar-list__event')
            if not event_articles:
                event_articles = soup.select('article.tribe-events-pro-photo__event, article.tribe-common-g-row')

            page_new_events = 0
            for article in event_articles:
                try:
                    event_data = extract_event_data(article, next_url)
                    if not event_data:
                        continue
                    event_url = event_data.get("url", "")
                    dedupe_key = event_url or f"{event_data.get('name', '')}::{event_data.get('startDate', '')}"
                    if dedupe_key in seen_urls:
                        continue
                    seen_urls.add(dedupe_key)
                    events.append(event_data)
                    page_new_events += 1
                except Exception as e:
                    print(f"Error processing GBC event: {e}")
                    continue

            next_link = (
                soup.select_one('a[rel="next"]')
                or soup.select_one('a.tribe-events-c-nav__next')
                or soup.select_one('a.next')
            )
            candidate_next = urljoin(next_url, next_link.get('href')) if next_link and next_link.get('href') else None
            if not candidate_next or candidate_next == next_url or page_new_events == 0:
                next_url = None
            else:
                next_url = candidate_next
        
        return events
        
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return []

def extract_event_data(article, base_url):
    """
    Extract event data from a single event article element
    """
    title_link = (
        article.find('a', class_='tribe-events-calendar-list__event-title-link')
        or article.select_one('.tribe-events-pro-photo__event-title a')
        or article.select_one('.tribe-events-calendar-list__event-title a')
        or article.select_one('h3 a, h2 a')
    )
    if not title_link:
        log_skip("missing_title_link")
        return None
        
    name = title_link.get_text(strip=True)
    event_url = urljoin(base_url, title_link.get('href', ''))
    
    datetime_elem = (
        article.find('time', class_='tribe-events-calendar-list__event-datetime')
        or article.select_one('time[datetime]')
    )
    if not datetime_elem:
        log_skip("missing_datetime", name)
        return None
    
    date_attr = datetime_elem.get('datetime')
    if not date_attr:
        log_skip("missing_datetime_attr", name)
        return None
    
    time_text = " ".join(datetime_elem.stripped_strings)
    start_date, end_date = parse_event_datetime(date_attr, time_text, article)
    if not start_date:
        log_skip("unparseable_datetime", name)
        return None
    
    description_elem = (
        article.find('div', class_='tribe-events-calendar-list__event-description')
        or article.select_one('.tribe-events-pro-photo__event-description')
        or article.select_one('.tribe-events-calendar-list__event-description-wrapper')
    )
    description = ""
    if description_elem:
        desc_text = description_elem.get_text(" ", strip=True)
        description = re.sub(r'\[.*?\]', '', desc_text).strip()
    
    venue_elem = (
        article.find('address', class_='tribe-events-calendar-list__event-venue')
        or article.select_one('address')
    )
    location = extract_location_data(venue_elem)
    
    event_type = extract_event_type(article)
    
    image_elem = (
        article.find('img', class_='tribe-events-calendar-list__event-featured-image')
        or article.select_one('img')
    )
    image_src = ""
    if image_elem:
        image_src = urljoin(
            base_url,
            first_present_attr(image_elem, 'src', 'data-src', 'data-lazy-src', 'data-srcset').split(',')[0].strip().split(' ')[0],
        )

    event_data = {
        "name": name,
        "startDate": start_date,
        "endDate": end_date,
        "endTime": end_date,
        "description": description,
        "url": event_url,
        "status": "ACTIVE",
        "location": location,
        "imageUrl": image_src,
        "eventType": event_type,
    }
    
    return event_data

def parse_event_datetime(date_attr, time_text, article=None):
    """
    Parse date and time information to create ISO format datetime strings
    """
    base_date = str(date_attr).strip()
    try:
        base_day = datetime.fromisoformat(base_date[:10]).date()
    except ValueError:
        return None, None

    attr_range = ""
    if article:
        attr_range = (
            first_present_attr(article, 'data-start-datetime', 'data-start-date')
            + " "
            + first_present_attr(article, 'data-end-datetime', 'data-end-date')
        )

    combined_text = " ".join(part for part in [time_text, attr_range] if part).strip()

    start_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', combined_text, re.IGNORECASE)
    if not start_match:
        start_dt = datetime(base_day.year, base_day.month, base_day.day, 12, 0, tzinfo=EASTERN_TZ)
        end_dt = datetime(base_day.year, base_day.month, base_day.day, 13, 0, tzinfo=EASTERN_TZ)
        return start_dt.isoformat(), end_dt.isoformat()

    start_hour = convert_to_24_hour(start_match.group(1), start_match.group(2), start_match.group(3))
    start_dt = datetime(
        base_day.year,
        base_day.month,
        base_day.day,
        start_hour[0],
        start_hour[1],
        tzinfo=EASTERN_TZ,
    )

    remaining_text = combined_text[start_match.end():]
    end_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', remaining_text, re.IGNORECASE)
    if end_match:
        end_hour = convert_to_24_hour(end_match.group(1), end_match.group(2), end_match.group(3))
        end_dt = datetime(
            base_day.year,
            base_day.month,
            base_day.day,
            end_hour[0],
            end_hour[1],
            tzinfo=EASTERN_TZ,
        )
        if end_dt < start_dt:
            end_dt = end_dt.replace(day=end_dt.day)  # keep explicit local date logic below
            end_dt = datetime.fromtimestamp(end_dt.timestamp() + 86400, tz=EASTERN_TZ)
    else:
        end_dt = datetime.fromtimestamp(start_dt.timestamp() + 3600, tz=EASTERN_TZ)

    return start_dt.isoformat(), end_dt.isoformat()

def convert_to_24_hour(hour_str, minute_str, period):
    """
    Convert 12-hour time format to 24-hour format
    """
    hour = int(hour_str)
    minute = int(minute_str or 0)
    
    if period == 'pm' and hour != 12:
        hour += 12
    elif period == 'am' and hour == 12:
        hour = 0
    
    return hour, minute

def extract_location_data(venue_elem):
    """
    Extract location information from venue element
    """
    location = {
        "name": "",
        "address": "",
        "city": "Baltimore",
        "state": "MD",
        "country": "US"
    }
    
    if venue_elem:
        venue_title = (
            venue_elem.find('span', class_='tribe-events-calendar-list__event-venue-title')
            or venue_elem.select_one('.tribe-events-venue-details')
            or venue_elem.select_one('strong')
        )
        if venue_title:
            location["name"] = venue_title.get_text(strip=True)
        
        venue_address = (
            venue_elem.find('span', class_='tribe-events-calendar-list__event-venue-address')
            or venue_elem.select_one('.tribe-events-pro-photo__event-venue')
            or venue_elem
        )
        if venue_address:
            address_text = venue_address.get_text(" ", strip=True)
            location["address"] = address_text
            
            city_state_match = re.search(r'([A-Za-z .-]+),\s*([A-Z]{2})\b', address_text)
            if city_state_match:
                location["city"] = city_state_match.group(1).strip()
                location["state"] = city_state_match.group(2).strip()
    
    return location

def extract_event_type(article):
    """
    Extract event type from the event type pill
    """
    type_pill = (
        article.find('div', class_='mg-events-type-pill')
        or article.select_one('[class*="type-pill"]')
    )
    if type_pill:
        type_text = type_pill.get_text(strip=True)
        return type_text
    return "In-Person"  # Default

def main():
    """
    Main function to run the scraper and output JSON
    """
    print("Scraping GBC events...")
    events = scrape_gbc_events()
    
    if events:
        print(f"Found {len(events)} events")
        # Output as formatted JSON
        json_output = json.dumps(events, indent=2)
        print("\nEvents JSON:")
        print(json_output)
        
        # Optionally save to file
        with open('gbc_events.json', 'w') as f:
            json.dump(events, f, indent=2)
        print("\nEvents saved to gbc_events.json")
    else:
        print("No events found or error occurred")

if __name__ == "__main__":
    main()
