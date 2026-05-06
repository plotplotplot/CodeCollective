from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


SOURCE_URL = (
    "https://www.baltimorecountymd.gov/departments/"
    "economic-and-workforce-development"
)
TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}


def scrape_events():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code == 403:
            print("Baltimore County DEWD source returned 403; skipping this cycle.")
            return []
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Baltimore County DEWD fetch error: {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    text = " ".join(soup.get_text(" ", strip=True).split()).lower()
    if "upcoming events" not in text:
        return []

    # DEWD frequently exposes event links through JS/event listings that may vary.
    # Return no-op when explicit event cards aren't discoverable from static HTML.
    return []


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_events(), indent=2))
