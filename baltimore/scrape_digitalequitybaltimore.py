from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.digitalequitybaltimore.org/general-clean"
TIMEZONE = ZoneInfo("America/New_York")
ORG_IMAGE_URL = (
    "https://static.wixstatic.com/media/8dc51b_7123df01d68e47a1b4b717c89ad4aea7~mv2.png"
    "/v1/fill/w_223,h_90,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/BDEC%20(1).png"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

DATE_RE = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December"
    r")\s+\d{1,2},\s+\d{4}\b",
    re.IGNORECASE,
)


def scrape_events(html: str | None = None) -> list[dict]:
    if html is None:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "html.parser")
    dates = _extract_coalition_call_dates(soup)
    scraped_at = datetime.now(TIMEZONE).isoformat()

    events = []
    for date_text in dates:
        start = datetime.strptime(date_text, "%B %d, %Y").replace(
            hour=12,
            minute=0,
            tzinfo=TIMEZONE,
        )
        end = start + timedelta(hours=1)
        events.append(
            {
                "name": "BDEC Coalition-Wide Meeting",
                "description": (
                    "Baltimore Digital Equity Coalition coalition-wide meeting, "
                    "held online every other month on the first Wednesday at 12:00 PM."
                ),
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "url": SOURCE_URL,
                "status": "ACTIVE",
                "location": {
                    "name": "Online",
                    "address": "Online",
                    "city": "Baltimore",
                    "state": "MD",
                    "country": "US",
                },
                "imageUrl": ORG_IMAGE_URL,
                "orgImageUrl": ORG_IMAGE_URL,
                "recurring": False,
                "scrapeTime": scraped_at,
                "tags": ["Economic Development", "Digital Equity", "Community"],
            }
        )

    return events


def _extract_coalition_call_dates(soup: BeautifulSoup) -> list[str]:
    heading = soup.find(
        string=lambda value: bool(value and "BDEC Coalition-Wide Meetings" in value)
    )
    if not heading:
        return []

    root = heading.find_parent("div")
    if root:
        root = root.find_parent("div")

    section_text = ""
    if root:
        for sibling in root.find_all_next("div", attrs={"data-testid": "richTextElement"}):
            text = sibling.get_text(" ", strip=True)
            if "Call for Member Events" in text:
                break
            section_text += f" {text}"

    if not section_text:
        section_text = soup.get_text(" ", strip=True)

    dates = []
    seen = set()
    for match in DATE_RE.finditer(section_text):
        date_text = re.sub(r"\s+", " ", match.group(0)).strip()
        key = date_text.lower()
        if key not in seen:
            seen.add(key)
            dates.append(date_text)

    return dates


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Digital Equity Baltimore events.")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    events = scrape_events()
    if args.debug:
        print(f"Scraped {len(events)} events from {SOURCE_URL}")
    print(json.dumps(events, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
