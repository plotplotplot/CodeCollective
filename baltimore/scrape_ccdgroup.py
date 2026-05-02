import hashlib
import json
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ccdgroup.org"
CONNECT_URL = f"{BASE_URL}/connect"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def _extract_event_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if "/event-details/" not in href:
            continue
        links.add(urljoin(CONNECT_URL, href.split("?")[0]))

    # Wix pages often include event links in script payloads as plain strings.
    marker = '"https://www.ccdgroup.org/event-details/'
    start = 0
    while True:
        idx = html.find(marker, start)
        if idx == -1:
            break
        end = html.find('"', idx + 1)
        if end == -1:
            break
        candidate = html[idx + 1:end].split("?")[0]
        links.add(candidate)
        start = end + 1

    return sorted(links)


def _extract_event_jsonld(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (script.string or script.get_text() or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if isinstance(item, dict) and str(item.get("@type", "")).lower() == "event":
                return item

    return None


def _normalize_event(event_url, event_jsonld, scrape_time):
    name = (event_jsonld.get("name") or "").strip()
    start_date = event_jsonld.get("startDate")
    end_date = event_jsonld.get("endDate") or start_date
    if not name or not start_date:
        return None

    location = event_jsonld.get("location") or {}
    image = event_jsonld.get("image") or {}
    image_url = image.get("url") if isinstance(image, dict) else (image[0] if isinstance(image, list) and image else "")

    stable_id_seed = f"{event_url}|{start_date}|{name}"
    event_id = hashlib.md5(stable_id_seed.encode("utf-8")).hexdigest()[:20]

    return {
        "id": event_id,
        "name": name,
        "description": (event_jsonld.get("description") or "").strip(),
        "startDate": start_date,
        "endTime": end_date,
        "url": event_url,
        "status": "ACTIVE",
        "location": {
            "name": (location.get("name") or "").strip() if isinstance(location, dict) else "",
            "address": (location.get("address") or "").strip() if isinstance(location, dict) else "",
        },
        "imageUrl": image_url or "",
        "recurring": False,
        "scrapeTime": scrape_time,
    }


def scrape_events():
    response = requests.get(CONNECT_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()

    links = _extract_event_links(response.text)
    events = []
    scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    for event_url in links:
        try:
            event_resp = requests.get(event_url, headers=HEADERS, timeout=20)
            event_resp.raise_for_status()
            event_jsonld = _extract_event_jsonld(event_resp.text)
            if not event_jsonld:
                continue
            normalized = _normalize_event(event_url, event_jsonld, scrape_time)
            if normalized:
                events.append(normalized)
        except Exception as exc:
            print(f"Warning: failed CCD event scrape for {event_url}: {exc}")

    return events
