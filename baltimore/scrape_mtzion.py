from datetime import datetime
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse


SOURCE_URL = "https://www.mtzionbaltimore.org/events/"
BASE_URL = "https://www.mtzionbaltimore.org"
DEFAULT_LOCATION = {
    "name": "Mt. Zion Church of Baltimore",
    "address": "3050 Liberty Heights Ave",
    "city": "Baltimore",
    "state": "MD",
    "postalCode": "21215",
    "country": "US",
}


def _infer_start(month_text: str, day_text: str, time_text: str) -> datetime:
    now = datetime.now()
    candidate = parse(f"{month_text} {day_text} {now.year} {time_text}")
    if candidate < now.replace(hour=0, minute=0, second=0, microsecond=0):
        next_year = now.year + 1 if candidate.month < now.month - 1 else now.year
        candidate = parse(f"{month_text} {day_text} {next_year} {time_text}")
    return candidate


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    events: List[Dict] = []

    for item in soup.select("div.event-main"):
        date_parts = [part.get_text(" ", strip=True) for part in item.select(".event-date-box span")]
        title_node = item.select_one(".event-item-content h3 a")
        time_node = item.select_one("span[id^='timeshow']")
        location_node = item.select_one("span[id^='locationshow']")
        image_node = item.select_one(".event-item-bg")
        description_node = item.select_one("div[id^='shortdesc']")

        if len(date_parts) < 2 or not title_node or not time_node:
            continue

        title = title_node.get_text(" ", strip=True)
        time_text = time_node.get_text(" ", strip=True)
        start_dt = _infer_start(date_parts[1], date_parts[0], time_text)
        href = title_node.get("onclick", "")
        slug = ""
        if "redirectPageTo('" in href:
            slug = href.split("redirectPageTo('", 1)[1].split("'", 1)[0]

        event: Dict = {
            "name": title,
            "description": description_node.get_text(" ", strip=True) if description_node else "",
            "startDate": start_dt.isoformat(),
            "url": urljoin(BASE_URL, slug) if slug else url,
            "status": "ACTIVE",
            "location": dict(DEFAULT_LOCATION),
            "recurring": False,
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        }
        if location_node and location_node.get_text(" ", strip=True):
            event["location"]["name"] = location_node.get_text(" ", strip=True)
        if image_node and image_node.get("data-src"):
            event["imageUrl"] = image_node["data-src"]

        events.append(event)

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
