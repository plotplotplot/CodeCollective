from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from http_client import build_session, polite_get


BASE_URL = "https://www.bccenter.org"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
EVENTS_ROOT = f"{BASE_URL}/events/"


def _iso_or_empty(value: str) -> str:
    if not value:
        return ""
    try:
        return date_parser.parse(value).isoformat()
    except Exception:
        return ""


def _event_urls_from_sitemap(xml_text: str) -> List[str]:
    urls: List[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return urls

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for node in root.findall("sm:url/sm:loc", ns):
        loc = (node.text or "").strip()
        loc_lower = loc.lower()
        if not loc.startswith(EVENTS_ROOT):
            continue
        if "/photogallery/" in loc_lower:
            continue
        if loc.rstrip("/").lower() == EVENTS_ROOT.rstrip("/").lower():
            continue
        urls.append(loc)
    return urls


def _parse_event_page(html: str, url: str) -> Dict | None:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("h1")
    if not title_el:
        return None
    name = " ".join(title_el.get_text(" ", strip=True).split()).strip()
    if not name:
        return None

    start_meta = soup.select_one('meta[itemprop="startDate"]')
    end_meta = soup.select_one('meta[itemprop="endDate"]')
    start_iso = _iso_or_empty((start_meta.get("content") if start_meta else "") or "")
    end_iso = _iso_or_empty((end_meta.get("content") if end_meta else "") or "")

    if not start_iso:
        # Fallback: parse "Date: June 02 - June 04, 2026" style text.
        date_label = soup.select_one(".eventDetailDetailDate")
        date_text = date_label.get_text(" ", strip=True) if date_label else ""
        match = re.search(
            r"([A-Za-z]+\s+\d{1,2})(?:\s*-\s*([A-Za-z]+\s+\d{1,2}|\d{1,2}))?,\s*(\d{4})",
            date_text,
        )
        if match:
            first_part, second_part, year = match.groups()
            first_full = f"{first_part}, {year}"
            start_iso = _iso_or_empty(first_full)
            if second_part:
                second_full = f"{second_part}, {year}" if re.search(r"[A-Za-z]", second_part) else f"{first_part.split()[0]} {second_part}, {year}"
                end_iso = _iso_or_empty(second_full)

    if not start_iso:
        return None

    loc_anchor = soup.select_one('.listingPageLocationDetails a[itemprop="location"]')
    location_name = " ".join(loc_anchor.get_text(" ", strip=True).split()).strip() if loc_anchor else ""

    desc_meta = soup.find("meta", attrs={"name": "description"})
    description = (desc_meta.get("content") or "").strip() if desc_meta else ""

    return {
        "name": name,
        "description": description,
        "startDate": start_iso,
        "endTime": end_iso,
        "url": url,
        "status": "ACTIVE",
        "location": {
            "name": location_name,
            "address": location_name,
        },
        "source": EVENTS_ROOT,
    }


def scrape_events(max_events: int = 120) -> List[Dict]:
    session = build_session()
    site_map_resp = polite_get(session, SITEMAP_URL, timeout=30)
    site_map_resp.raise_for_status()

    candidate_urls = _event_urls_from_sitemap(site_map_resp.text)
    events: List[Dict] = []
    seen = set()

    for url in candidate_urls[:max_events]:
        try:
            detail_resp = polite_get(session, url, timeout=30)
            detail_resp.raise_for_status()
            event = _parse_event_page(detail_resp.text, url)
        except Exception:
            continue

        if not event:
            continue

        key = (event.get("name", "").strip().lower(), event.get("startDate", ""))
        if key in seen:
            continue
        seen.add(key)
        events.append(event)

    today = datetime.now().date()
    filtered: List[Dict] = []
    for event in events:
        try:
            start = date_parser.parse(str(event.get("startDate", ""))).date()
        except Exception:
            continue
        if start >= today:
            filtered.append(event)

    return sorted(filtered, key=lambda ev: ev.get("startDate", ""))
