from datetime import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse


SOURCE_URL = "https://columbiapres.org/"
DEFAULT_LOCATION = {
    "name": "Columbia Presbyterian Church",
    "address": "7100 Columbia Gateway Dr",
    "city": "Columbia",
    "state": "MD",
    "postalCode": "21046",
    "country": "US",
}


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    events: List[Dict] = []

    for article in soup.select("article.ctc_event.type-ctc_event"):
        title_link = article.select_one("h3 a")
        date_node = article.select_one(".jubilee-event-compact-date time")
        time_node = article.select_one(".jubilee-event-compact-time")
        image_node = article.select_one("img")

        if not title_link or not date_node:
            continue

        date_text = date_node.get("datetime") or date_node.get_text(" ", strip=True)
        time_text = time_node.get_text(" ", strip=True) if time_node else ""
        start_dt = parse(f"{date_text} {time_text.split('–')[0].strip()}") if time_text else parse(date_text)

        end_dt = None
        if "–" in time_text:
            end_dt = parse(f"{date_text} {time_text.split('–', 1)[1].strip()}")

        event: Dict = {
            "name": title_link.get_text(" ", strip=True),
            "description": "",
            "startDate": start_dt.isoformat(),
            "url": title_link.get("href"),
            "status": "ACTIVE",
            "location": dict(DEFAULT_LOCATION),
            "recurring": False,
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        }
        if end_dt:
            event["endTime"] = end_dt.isoformat()
        if image_node and image_node.get("src"):
            event["imageUrl"] = image_node["src"]

        events.append(event)

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
