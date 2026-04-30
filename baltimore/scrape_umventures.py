import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo
from dateutil.parser import parse

URL = "https://www.umventures.org/events"
TIMEZONE = ZoneInfo("America/New_York")

DEFAULT_LOCATION = {
    "name": "UM Ventures",
    "address": "",
    "city": "Baltimore",
    "state": "MD",
    "country": "US",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.umventures.org/",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

def fetch_html(url: str) -> str:
    session = requests.Session()
    session.headers.update(HEADERS)

    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text

def scrape_events() -> list[dict]:
    # Page is protected by Cloudflare TLS Challenge
    return []
    scraped_at = datetime.now(TIMEZONE).isoformat()
    html = fetch_html(URL)
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for h2 in soup.select("h2 a[href]"):
        name = h2.get_text(" ", strip=True)
        link = urljoin(URL, h2["href"])

        parent_h2 = h2.find_parent("h2")
        if not parent_h2:
            continue

        date_el = parent_h2.find_next_sibling()
        if not date_el:
            continue

        date_str = date_el.get_text(" ", strip=True)
        if not date_str:
            continue

        try:
            start_dt = parse(date_str, fuzzy=True)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=TIMEZONE)
            else:
                start_dt = start_dt.astimezone(TIMEZONE)
        except Exception:
            continue

        events.append({
            "name": name,
            "description": "",
            "startDate": start_dt.isoformat(),
            "url": link,
            "status": "ACTIVE",
            "location": dict(DEFAULT_LOCATION),
            "recurring": False,
            "scrapeTime": scraped_at,
        })

    return events