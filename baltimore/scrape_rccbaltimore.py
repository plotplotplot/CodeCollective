from datetime import datetime
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse


SOURCE_URL = "https://www.rccbaltimore.org/events-1"
DEFAULT_IMAGE = "https://images.squarespace-cdn.com/content/v1/602ff95edc8bf42c73c4d24a/1518921092755-Q3BHQ50E6B0K34KM278Q/logo+only.png?format=1500w"


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    events: List[Dict] = []

    for item in soup.select(".eventlist-event"):
        title_link = item.select_one(".eventlist-title-link")
        date_node = item.select_one(".event-date")
        start_node = item.select_one(".event-time-localized-start")
        end_node = item.select_one(".event-time-localized-end")
        address_item = item.select_one(".eventlist-meta-address")
        description_node = item.select_one(".eventlist-description")

        if not title_link or not date_node or not start_node:
            continue

        start_dt = parse(f"{date_node.get_text(' ', strip=True)} {start_node.get_text(' ', strip=True)}")
        end_dt = parse(f"{date_node.get_text(' ', strip=True)} {end_node.get_text(' ', strip=True)}") if end_node else None

        location_name = ""
        location_text = ""
        if address_item:
            text_parts = list(address_item.stripped_strings)
            location_name = text_parts[0] if text_parts else ""
            map_link = address_item.select_one(".eventlist-meta-address-maplink")
            if map_link and map_link.get("href"):
                location_text = map_link.get("href").split("q=", 1)[-1].strip()

        event: Dict = {
            "name": title_link.get_text(" ", strip=True),
            "description": description_node.get_text(" ", strip=True) if description_node else "",
            "startDate": start_dt.isoformat(),
            "url": urljoin(url, title_link.get("href", "")),
            "status": "ACTIVE",
            "imageUrl": DEFAULT_IMAGE,
            "recurring": False,
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        }

        if end_dt:
            event["endTime"] = end_dt.isoformat()

        if location_name or location_text:
            event["location"] = {
                "name": location_name or "Redemption City Church",
                "address": location_text or location_name,
                "city": "Baltimore",
                "state": "MD",
                "country": "US",
            }

        events.append(event)

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
