#!/usr/bin/env python3
"""Scrape Maryland General Assembly sponsor/member data to JSON.

Uses `wget` for network fetches, including member pages and images.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

BASE_URL = "https://mgaleg.maryland.gov"
INDEX_PATHS = {
    "senate": "/mgawebsite/Members/Index/senate",
    "house": "/mgawebsite/Members/Index/house",
}


def fetch_bytes_with_wget(url: str, timeout: int = 60) -> bytes:
    cmd = ["wget", "-q", "-O", "-", "--timeout", str(timeout), url]
    proc = subprocess.run(cmd, check=False, capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"wget failed ({proc.returncode}) for {url}: {err}")
    return proc.stdout


def fetch_html(url: str) -> BeautifulSoup:
    payload = fetch_bytes_with_wget(url)
    return BeautifulSoup(payload, "html.parser")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def split_lines(value: str) -> list[str]:
    return [clean_text(x) for x in re.split(r"[\r\n]+", value) if clean_text(x)]


def link_to_slug(href: str) -> str | None:
    match = re.search(r"/mgawebsite/Members/Details/([^/?#]+)", href)
    return match.group(1) if match else None


def collect_member_links() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for chamber, path in INDEX_PATHS.items():
        soup = fetch_html(urljoin(BASE_URL, path))
        for anchor in soup.select('a[href*="/mgawebsite/Members/Details/"]'):
            href = anchor.get("href", "")
            slug = link_to_slug(href)
            if not slug:
                continue
            key = f"{chamber}:{slug}"
            if key in seen:
                continue
            seen.add(key)
            out.append((chamber, slug))
    return out


def safe_slug(value: str) -> str:
    value = unquote(value)
    value = re.sub(r"[^a-zA-Z0-9._-]+", "_", value)
    return value.strip("_") or "member"


def image_payload(src: str | None, slug: str, kind: str, image_root: Path) -> dict[str, Any] | None:
    if not src:
        return None
    full_url = urljoin(BASE_URL, src)
    mime = mimetypes.guess_type(full_url)[0] or "application/octet-stream"
    ext = mimetypes.guess_extension(mime) or Path(src).suffix or ".bin"
    filename = f"{safe_slug(slug)}_{kind}{ext}"
    local_path = image_root / filename
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if not local_path.exists():
        raw = fetch_bytes_with_wget(full_url)
        local_path.write_bytes(raw)

    return {
        "url": full_url,
        "mime_type": mime,
        "local_path": str(local_path.as_posix()),
        "path": "/" + local_path.as_posix(),
    }


def parse_detail(chamber: str, slug: str, pause_seconds: float, image_root: Path) -> dict[str, Any]:
    detail_url = urljoin(BASE_URL, f"/mgawebsite/Members/Details/{slug}")
    soup = fetch_html(detail_url)
    h2 = soup.find("h2")
    header = clean_text(h2.get_text(" ", strip=True)) if h2 else ""

    main_tab = soup.find(id="divMain") or soup
    dl = main_tab.select_one("dl.row")
    fields: dict[str, str] = {}
    if dl:
        for dt in dl.select("dt"):
            dd = dt.find_next_sibling("dd")
            if dd is None:
                continue
            key = clean_text(dt.get_text(" ", strip=True))
            val = clean_text(dd.get_text("\n", strip=True))
            fields[key] = val

    committees = split_lines(fields.get("Committee Assignment(s)", ""))
    contact_dd = None
    for dt in main_tab.select("dt"):
        if clean_text(dt.get_text(" ", strip=True)).lower() == "contact":
            contact_dd = dt.find_next_sibling("dd")
            break
    emails: list[str] = []
    newsletter_url = None
    if contact_dd:
        for a in contact_dd.select('a[href^="mailto:"]'):
            href = a.get("href", "")
            email = href.split("mailto:", 1)[-1].split("?", 1)[0].strip()
            if email and email not in emails:
                emails.append(email)
            label = clean_text(a.get_text(" ", strip=True)).lower()
            if "newsletter" in label:
                newsletter_url = href

    portrait_img = main_tab.select_one("img.details-page-image-padding")
    district_img = None
    for img in main_tab.select("img"):
        src = img.get("src", "")
        if "DistrictCloseUps" in src:
            district_img = img
            break

    result = {
        "chamber": chamber,
        "slug": slug,
        "detail_url": detail_url,
        "name_heading": header,
        "district": fields.get("District"),
        "county": fields.get("County"),
        "party": fields.get("Party"),
        "committee_assignments": committees,
        "annapolis_info": split_lines(fields.get("Annapolis Info", "")),
        "interim_info": split_lines(fields.get("Interim Info", "")),
        "contact_emails": emails,
        "newsletter_mailto": newsletter_url,
        "main_fields": fields,
        "portrait_image": image_payload(portrait_img.get("src") if portrait_img else None, slug, "portrait", image_root),
        "district_map_image": image_payload(district_img.get("src") if district_img else None, slug, "district_map", image_root),
    }

    if pause_seconds > 0:
        time.sleep(pause_seconds)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape MGA sponsor/member data.")
    parser.add_argument(
        "--output",
        default="data/mga_sponsors_2026.json",
        help="Output JSON path (default: data/mga_sponsors_2026.json)",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.05,
        help="Pause seconds between detail-page requests (default: 0.05)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of members for testing (0 = no limit)",
    )
    parser.add_argument(
        "--image-dir",
        default="images/politicians",
        help="Directory to store downloaded images (default: images/politicians)",
    )
    args = parser.parse_args()

    members = collect_member_links()
    if args.limit > 0:
        members = members[: args.limit]
    image_root = Path(args.image_dir)

    records = []
    for idx, (chamber, slug) in enumerate(members, start=1):
        print(f"[{idx}/{len(members)}] {chamber}:{slug}")
        records.append(parse_detail(chamber, slug, args.pause, image_root))

    output = {
        "source": "https://mgaleg.maryland.gov/mgawebsite/Members",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "records": records,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} records to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
