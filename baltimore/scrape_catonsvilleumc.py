from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse


SOURCE_URL = "https://www.catonsvilleumc.org/upcoming-events/"
DEFAULT_IMAGE = "https://www.catonsvilleumc.org/wp-content/uploads/2019/11/CUMClogo.png"
DEFAULT_LOCATION = {
    "name": "Catonsville United Methodist Church",
    "address": "6 Melvin Ave.",
    "city": "Catonsville",
    "state": "MD",
    "postalCode": "21228",
    "country": "US",
}


def parse_date_and_time(date_text: str, time_text: str) -> Tuple[Optional[str], Optional[str]]:
    if not date_text:
        return None, None

    normalized_date = date_text.replace("\xa0", " ").strip()
    if "–" in normalized_date:
        normalized_date = normalized_date.split("–")[-1].strip()

    start_time_text = time_text or ""
    end_time_text = ""
    if "–" in start_time_text:
        start_time_text, end_time_text = [part.strip() for part in start_time_text.split("–", 1)]

    start_dt = parse(f"{normalized_date} {start_time_text}") if start_time_text else parse(normalized_date)
    end_dt = parse(f"{normalized_date} {end_time_text}") if end_time_text else None

    return start_dt.isoformat(), end_dt.isoformat() if end_dt else None


def scrape_events(url: str = SOURCE_URL) -> List[Dict]:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    events: List[Dict] = []

    for article in soup.select("article.saved-event-short"):
        title_link = article.select_one(".saved-entry-short-title a")
        date_node = article.select_one(".saved-entry-short-date")
        time_node = article.select_one(".saved-event-short-time")
        recurrence_node = article.select_one(".saved-entry-short-recurrence")
        excerpt_node = article.select_one(".saved-entry-content-short")

        if not title_link or not date_node:
            continue

        start_date, end_time = parse_date_and_time(
            date_node.get_text(" ", strip=True),
            time_node.get_text(" ", strip=True) if time_node else "",
        )

        if not start_date:
            continue

        event = {
            "name": title_link.get_text(" ", strip=True),
            "description": excerpt_node.get_text(" ", strip=True) if excerpt_node else "",
            "startDate": start_date,
            "endTime": end_time,
            "url": title_link.get("href"),
            "status": "ACTIVE",
            "location": dict(DEFAULT_LOCATION),
            "imageUrl": DEFAULT_IMAGE,
            "recurring": bool(recurrence_node),
            "scrapeTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        }

        events.append(event)

    return events


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
