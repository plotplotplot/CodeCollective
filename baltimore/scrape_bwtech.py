import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://bwtech.umbc.edu"
START_URL = "https://bwtech.umbc.edu/events/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EventScraper/1.0; +https://example.com/bot)"
}

def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    # a few sane retry settings
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def parse_event_links(html, base=BASE_URL):
    """
    From an events archive page, return absolute links for each event card.
    """
    soup = BeautifulSoup(html, "html.parser")
    links = []

    # Your selector
    for a in soup.select("div.cards-container.news-cards div.card .card-bottom a.link-title"):
        href = a.get("href")
        if href:
            links.append(urljoin(base, href))

    # Fallback(s) for common The Events Calendar list/archive templates
    if not links:
        for a in soup.select(".tribe-events-calendar-list__event-title a, .tribe-event-url, h3.tribe-events-calendar-list__event-title a"):
            href = a.get("href")
            if href:
                links.append(urljoin(base, href))

    # De-dupe, keep order
    out, seen = [], set()
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def find_next_page(html, base=BASE_URL):
    """
    Try to find the next archive page (pagination). Returns absolute URL or None.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Prefer rel="next" if present
    link_next = soup.find("link", rel="next")
    if link_next and link_next.get("href"):
        return urljoin(base, link_next["href"])

    # Fallbacks (if site theme changes): look for pagination anchors named Next
    for a in soup.select("a"):
        txt = (a.get_text(strip=True) or "").lower()
        if txt in {"next", "›", "»"}:
            href = a.get("href")
            if href:
                return urljoin(base, href)

    return None

def fetch(session, url, sleep=0.5):
    """
    GET a URL with a tiny delay to be polite.
    """
    time.sleep(sleep)
    r = session.get(url, timeout=20)
    r.raise_for_status()
    return r.text

def _text_or_none(el):
    return el.get_text(" ", strip=True) if el else None

def _meta(soup, prop=None, name=None):
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return tag["content"]
    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"]
    return None

def _first_str(*vals):
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _parse_jsonld_events(soup):
    """
    Return a list of dicts for any JSON-LD @type=Event found in Yoast's schema graph.
    """
    out = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or script.get_text() or "")
        except Exception:
            continue

        # Normalize to list of graph nodes
        nodes = []
        if isinstance(data, dict) and "@graph" in data and isinstance(data["@graph"], list):
            nodes = data["@graph"]
        elif isinstance(data, list):
            nodes = data
        elif isinstance(data, dict):
            nodes = [data]

        for n in nodes:
            try:
                if isinstance(n, dict) and n.get("@type") == "Event":
                    out.append(n)
            except Exception:
                continue
    return out

def _compose_address(addr_obj):
    if not isinstance(addr_obj, dict):
        return None
    parts = [
        addr_obj.get("streetAddress"),
        addr_obj.get("addressLocality"),
        addr_obj.get("addressRegion"),
        addr_obj.get("postalCode"),
    ]
    # Clean empties, join with ", " but avoid duplicate commas
    parts = [p for p in parts if isinstance(p, str) and p.strip()]
    return ", ".join(parts) if parts else None

def parse_event_page(html, url):
    """
    Parse an individual event page into the target schema.
    IMPORTANT: scrapeTime comes from article:modified_time when available.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Prefer JSON-LD Event block if present
    jsonld_events = _parse_jsonld_events(soup)
    ev_ld = jsonld_events[0] if jsonld_events else {}

    # Title / Name
    name = _first_str(
        ev_ld.get("name"),
        _meta(soup, prop="og:title"),
        _text_or_none(soup.select_one("h1.entry-title, h1.tribe-events-single-event-title, .tribe-events-single-event-title")),
    )

    # Description
    desc = _first_str(
        ev_ld.get("description"),
        _meta(soup, prop="og:description"),
        _text_or_none(soup.select_one(".tribe-events-single-event-description, .entry-content, .text-content")),
    )

    # Dates
    start_iso = _first_str(ev_ld.get("startDate"))
    end_iso = _first_str(ev_ld.get("endDate"))

    # In case the page shows "October 14 @ 11:30 am - 1:30 pm" and JSON-LD is missing (unlikely here),
    # you could add a fallback parser — but JSON-LD should be reliable on this site.

    # Location
    loc = ev_ld.get("location") or {}
    loc_name = ""
    loc_addr = ""
    if isinstance(loc, dict):
        loc_name = loc.get("name")
        addr_obj = loc.get("address") if isinstance(loc.get("address"), dict) else {}
        loc_addr = _compose_address(addr_obj)

    # Image
    image_url = _first_str(
        (ev_ld.get("image") or {}).get("url") if isinstance(ev_ld.get("image"), dict) else None,
        _meta(soup, prop="og:image")
    )

    # Status (default ACTIVE if scheduled)
    status_from_ld = ev_ld.get("eventStatus")
    # Map schema.org status to simple label
    status = "ACTIVE"
    if isinstance(status_from_ld, str):
        s = status_from_ld.lower()
        if "cancelled" in s:
            status = "CANCELLED"
        elif "postponed" in s:
            status = "POSTPONED"

    # scrapeTime from article:modified_time (as requested)
    modified = _meta(soup, prop="article:modified_time")
    if not modified:
        # fallback: now in UTC ISO-like with space (to match your sample format closely)
        modified = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Build the final object
    event_obj = {
        "name": name,
        "description": desc,
        "startDate": start_iso,     # e.g., "2025-10-14T11:30:00-04:00"
        "endTime": end_iso,         # your schema uses "endTime"
        "url": url,
        "status": status,
        "location": {
            "name": loc_name,
            "address": loc_addr
        },
        "imageUrl": image_url,
        "scrapeTime": modified
    }

    return event_obj

def scrape_events(pages=1, max_workers=6):
    """
    Scrape the first `pages` of the Events archive.
    Set pages=None to crawl until pagination ends (be respectful).
    Returns a list of dicts in your target schema.
    """
    session = get_session()

    all_event_links = []
    page_url = START_URL
    page_count = 0

    while page_url and (pages is None or page_count < pages):
        html = fetch(session, page_url)
        links = parse_event_links(html)
        all_event_links.extend(links)
        page_count += 1
        next_url = find_next_page(html)
        page_url = next_url if next_url and next_url != page_url else None

    # Deduplicate while preserving order
    seen = set()
    unique_links = []
    for link in all_event_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    print(f"Found {len(unique_links)} event links.")

    # Fetch each event page (in parallel for speed)
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(fetch, session, url): url for url in unique_links}
        for fut in as_completed(future_to_url):
            url = future_to_url[fut]
            try:
                html = fut.result()
                data = parse_event_page(html, url)
                results.append(data)
            except Exception as e:
                print(f"[WARN] Failed {url}: {e}")

    return results

if __name__ == "__main__":
    # Scrape just the first page by default.
    items = scrape_events(pages=1)
    # Pretty-print JSON array
    print(json.dumps(items, indent=4, ensure_ascii=False))
