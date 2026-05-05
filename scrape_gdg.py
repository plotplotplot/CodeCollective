#!/usr/bin/env python3
"""
Scrape GDG (Bevy) chapter events via the public JSON endpoints and emit a normalized list.

Example:
  python3 scrape_gdg_events.py --chapter-id 3047 --page-size 50 > gdg-baltimore-events.json

Notes:
- The GDG API often returns 406 unless you send browser-like headers (Accept, User-Agent, etc.).
- The "event_slim" payload does not always include location/end time; those fields will be left blank.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from http_client import polite_get, build_session


BASE = "https://gdg.community.dev"


@dataclass(frozen=True)
class ScrapeConfig:
    chapter_id: int
    page_size: int
    include_cohosted_events: bool
    visible_on_parent_chapter_only: bool
    timeout_s: float


def _now_scrape_time_str() -> str:
    # Match your example style: "YYYY-MM-DD HH:MM:SS[.ffffff]"
    # We'll use second precision by default.
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _stable_id_from_url(url: str) -> str:
    # Your example uses a 32-hex id; produce one deterministically from the URL.
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def _headers() -> Dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": f"{BASE}/",
        "Origin": BASE,
        "X-Requested-With": "XMLHttpRequest",
    }


def _extract_results(payload: Any) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Returns (results, next_url_or_token)
    Supports common pagination shapes:
      - {"results":[...], "next":"https://...page=2"}
      - {"data":[...], "next":...}
      - {"results":[...], "next_page":...}
      - Plain list [...]
    """
    if isinstance(payload, list):
        return payload, None

    if not isinstance(payload, dict):
        return [], None

    for key in ("results", "data", "items"):
        if key in payload and isinstance(payload[key], list):
            next_val = payload.get("next") or payload.get("next_page") or payload.get("nextPageToken")
            return payload[key], (str(next_val) if next_val else None)

    # Some APIs might wrap as {"count":..., "results":...} etc. Already handled above.
    return [], None


def _normalize_event(item: Dict[str, Any], status_out: str, scrape_time: str) -> Dict[str, Any]:
    # The "event_slim" fields you requested in your network log:
    # title, start_date, event_type_title, cropped_picture_url, cropped_banner_url, url, description, description_short
    title = item.get("title") or item.get("name") or ""
    start_date = item.get("start_date") or item.get("startDate") or ""

    url = item.get("url") or ""
    if url and url.startswith("/"):
        url = f"{BASE}{url}"

    # Some payloads might include "id" or "uuid"; prefer that if present.
    raw_id = item.get("id") or item.get("uuid") or item.get("event_uuid") or ""
    event_id = str(raw_id) if raw_id else (_stable_id_from_url(url) if url else _stable_id_from_url(title + start_date))

    # Prefer banner, then picture
    image = item.get("cropped_banner_url") or item.get("cropped_picture_url") or item.get("picture") or ""
    if isinstance(image, str) and image.startswith("/"):
        image = f"{BASE}{image}"

    desc = item.get("description_short") or item.get("description") or ""

    # Location/end time are often not present in event_slim; keep empty but preserve schema.
    return {
        "id": event_id,
        "name": title,
        "startDate": start_date,
        "endDate": "",
        "description": desc,
        "url": url,
        "status": status_out,
        "location": {
            "name": "",
            "address": "",
            "latitude": None,
            "longitude": None,
        },
        "imageUrl": image,
        "recurring": False,
        "scrapeTime": scrape_time,
    }


def fetch_events(cfg: ScrapeConfig, status_in: str) -> List[Dict[str, Any]]:
    """
    status_in: "Live" or "Completed" (as used by the GDG API)
    """
    endpoint = f"{BASE}/api/event_slim/for_chapter/{cfg.chapter_id}/"

    # Include "id" in fields in case it exists (won't hurt if ignored).
    fields = ",".join(
        [
            "id",
            "title",
            "start_date",
            "end_date",
            "event_type_title",
            "cropped_picture_url",
            "cropped_banner_url",
            "url",
            "cohost_registration_url",
            "description",
            "description_short",
        ]
    )

    params_base = {
        "page_size": cfg.page_size,
        "status": status_in,
        "include_cohosted_events": "true" if cfg.include_cohosted_events else "false",
        "visible_on_parent_chapter_only": "true" if cfg.visible_on_parent_chapter_only else "false",
        "order": "start_date" if status_in.lower() == "live" else "-start_date",
        "fields": fields,
    }

    out_status = "ACTIVE" if status_in.lower() == "live" else "COMPLETED"
    scrape_time = _now_scrape_time_str()

    session = build_session()
    session.headers.update(_headers())

    all_items: List[Dict[str, Any]] = []
    page = 1
    next_url: Optional[str] = None

    while True:
        if next_url:
            resp = polite_get(session, next_url, timeout=cfg.timeout_s)
        else:
            params = dict(params_base)
            params["page"] = page
            resp = polite_get(session, endpoint, params=params, timeout=cfg.timeout_s)

        # Raise helpful error if blocked
        if resp.status_code == 406:
            raise RuntimeError(
                "Got 406 Not Acceptable. The API is rejecting your request. "
                "Try running from a normal network, or adjust headers in _headers()."
            )

        resp.raise_for_status()

        payload = resp.json()
        results, next_val = _extract_results(payload)

        if not results:
            break

        for item in results:
            if isinstance(item, dict):
                all_items.append(_normalize_event(item, out_status, scrape_time))

        # Pagination: if API provides "next" URL use it; otherwise fall back to page increment.
        if next_val:
            # Some APIs return a full URL in "next"
            next_url = next_val if next_val.startswith("http") else None
            if next_url:
                continue

        # Fallback heuristic: stop when fewer than page_size returned
        if len(results) < cfg.page_size:
            break

        page += 1

    return all_items

def scrapeChapterID(chapterID = 3047):
    cfg = ScrapeConfig(
        chapter_id=chapterID,
        page_size=50,
        include_cohosted_events=True,
        visible_on_parent_chapter_only=False,
        timeout_s=10,
    )
    return scrape(cfg)

def scrape(cfg):

    events: List[Dict[str, Any]] = []
    events.extend(fetch_events(cfg, "Live"))
    events.extend(fetch_events(cfg, "Completed"))

    # Emit as the exact list format you showed.
    return events


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter-id", type=int, required=True, help="GDG chapter numeric id (e.g. 3047 for GDG Baltimore)")
    ap.add_argument("--page-size", type=int, default=50, help="How many events per page to request")
    ap.add_argument("--no-cohosted", action="store_true", help="Exclude co-hosted events")
    ap.add_argument("--no-parent-only", action="store_true", help="Disable visible_on_parent_chapter_only filter")
    ap.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout seconds")
    args = ap.parse_args(argv)

    cfg = ScrapeConfig(
        chapter_id=args.chapter_id,
        page_size=max(1, min(200, args.page_size)),
        include_cohosted_events=not args.no_cohosted,
        visible_on_parent_chapter_only=not args.no_parent_only,
        timeout_s=args.timeout,
    )
    print(json.dumps(scrape(cfg),indent=2))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
