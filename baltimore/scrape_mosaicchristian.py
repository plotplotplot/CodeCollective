from datetime import datetime
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse


SOURCE_URL = "https://mosaicchristian.org/events/"
BASE_URL = "https://mosaicchristian.org"
DEFAULT_LOCATION = {
    "name": "Mosaic Christian Church",
    "address": "Dorsey Station Dr",
    "city": "Elkridge",
    "state": "MD",
    "postalCode": "21075",
    "country": "US",
}


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    events: List[Dict] = []

    for panel in soup.select("#events-list .panel"):
        title_node = panel.select_one(".c-item__title")
        date_parts = panel.select(".c-event__sub div span")
        calendar_link = panel.select_one("a[href*='export.ics.php']")
        learn_more_link = panel.select_one("a[href^='/event/']")
        category_node = panel.select_one(".c-item__cat")

        if not title_node or len(date_parts) < 4:
            continue

        date_text = date_parts[1].get_text(" ", strip=True).replace("\xa0", " ")
        time_text = date_parts[3].get_text(" ", strip=True).replace("\xa0", " ")
        start_dt = parse(f"{date_text} {time_text}")

        event: Dict = {
            "name": title_node.get_text(" ", strip=True),
            "description": category_node.get_text(" ", strip=True) if category_node else "",
            "startDate": start_dt.isoformat(),
            "url": urljoin(BASE_URL, learn_more_link.get("href", "")) if learn_more_link else url,
            "status": "ACTIVE",
            "location": dict(DEFAULT_LOCATION),
            "recurring": False,
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        }
        if calendar_link and calendar_link.get("href"):
            event["icsUrl"] = calendar_link.get("href")

        events.append(event)

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
