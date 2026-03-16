#!/usr/bin/env python3
"""Fetch Baltimore City Council hearing and testimony metadata for local/static use."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from collections import OrderedDict
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen


BASE_URL = "https://baltimore.legistar.com/"
CALENDAR_URL = urljoin(BASE_URL, "Calendar.aspx")
OFFICIAL_MEMBERS_URL = "https://www.baltimorecity.gov/city-council/members-and-committees/city-council-members"
USER_AGENT = "CodeCollective-CityCouncilCache/1.0"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = SCRIPT_DIR / "data" / "city_council_testimony.json"
IMAGES_DIR = SCRIPT_DIR / "images"
KNOWN_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".img")
LINK_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
CARD_RE = re.compile(
    r'<div class="views-row">.*?<img[^>]+src="([^"]+)"[^>]*>.*?<H3>\s*(.*?)\s*</H3>.*?<a href="([^"]+)"><span class="link-arrow">Read Bio</span></a>',
    re.IGNORECASE | re.DOTALL,
)
BIO_RE = re.compile(
    r'<div class="bio-wrapper">.*?<h2[^>]*>\s*About.*?</h2>\s*(.*?)(?:<h3>\s*Contact Information\s*</h3>|</div>)',
    re.IGNORECASE | re.DOTALL,
)


def fetch_text(url: str, timeout: int = 60) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def fetch_binary(url: str, timeout: int = 60) -> tuple[bytes, str]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310
        payload = resp.read()
        content_type = resp.headers.get_content_type()
    return payload, content_type


def clean_html_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", unescape(TAG_RE.sub(" ", value or ""))).strip()


def html_block_to_paragraph_text(value: str) -> str:
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", value or "", re.IGNORECASE | re.DOTALL)
    cleaned = [clean_html_text(paragraph) for paragraph in paragraphs]
    return "\n\n".join(paragraph for paragraph in cleaned if paragraph)


def strip_contact_trailer(text: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    kept: list[str] = []
    for paragraph in paragraphs:
        if (
            "100 holliday street" in paragraph.lower()
            or "@baltimorecity.gov" in paragraph.lower()
            or re.search(r"\b410-\d{3}-\d{4}\b", paragraph)
        ):
            break
        kept.append(paragraph)
    return "\n\n".join(kept).strip()


def normalize_url(href: str) -> str:
    return urljoin(BASE_URL, unescape(href))


def extract_links(html: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for href, label in LINK_RE.findall(html):
        text = clean_html_text(label)
        if not href or not text:
            continue
        links.append({"url": normalize_url(href), "label": text})
    return links


def extract_calendar_meetings(html: str) -> list[dict[str, str]]:
    meetings: OrderedDict[str, dict[str, str]] = OrderedDict()
    for link in extract_links(html):
        if "MeetingDetail.aspx" not in link["url"]:
            continue
        meeting = meetings.setdefault(link["url"], {"meeting_url": link["url"], "meeting_name": link["label"]})
        if link["label"]:
            meeting["meeting_name"] = link["label"]
    return list(meetings.values())


def extract_element_text_by_id(html: str, element_id: str) -> str:
    pattern = re.compile(
        rf'<(?:span|a)[^>]+id="{re.escape(element_id)}"[^>]*>(.*?)</(?:span|a)>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html)
    return clean_html_text(match.group(1)) if match else ""


def extract_links_from_element(html: str, element_id: str) -> list[dict[str, str]]:
    pattern = re.compile(
        rf'<(?:span|td)[^>]+id="{re.escape(element_id)}"[^>]*>(.*?)</(?:span|td)>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html)
    return extract_links(match.group(1)) if match else []


def extract_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    title = clean_html_text(match.group(1))
    return re.sub(r"\s+-\s+.*$", "", title).strip()


def split_title_and_summary(value: str) -> tuple[str, str]:
    normalized = unescape(value or "").replace("\r", "")
    parts = [part.strip() for part in re.split(r"\n\s*\n+", normalized) if part.strip()]
    if not parts:
        return "", ""
    headline = WHITESPACE_RE.sub(" ", parts[0]).strip()
    summary = WHITESPACE_RE.sub(" ", " ".join(parts[1:])).strip()
    return headline, summary


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "portrait"


def normalize_person_name(value: str) -> str:
    value = unescape(value or "")
    value = re.sub(r",\s*District\s+\d+.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\b(council vice-president|council vice president|vice president|council president|city council member|council member)\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r'["“”]', "", value)
    value = re.sub(r"[^a-zA-Z0-9\s'-]", " ", value)
    return WHITESPACE_RE.sub(" ", value).strip().lower()


def person_name_candidates(value: str) -> list[str]:
    normalized = normalize_person_name(value)
    if not normalized:
        return []
    tokens = normalized.split()
    candidates = {normalized}
    if len(tokens) >= 2:
        candidates.add(f"{tokens[0]} {tokens[-1]}")
    return [candidate for candidate in candidates if candidate]


def choose_extension(url: str, content_type: str) -> str:
    path_ext = Path(urlparse(url).path).suffix.lower()
    if path_ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return path_ext
    guessed = mimetypes.guess_extension(content_type or "")
    return guessed or ".img"


def save_remote_image(url: str, output_dir: Path, slug: str) -> str:
    payload, content_type = fetch_binary(url)
    extension = choose_extension(url, content_type)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}{extension}"
    path = output_dir / filename
    path.write_bytes(payload)
    return f"images/{filename}"


def find_existing_image(output_dir: Path, slug: str) -> str | None:
    for extension in KNOWN_IMAGE_EXTENSIONS:
        path = output_dir / f"{slug}{extension}"
        if path.exists():
            return f"images/{path.name}"
    return None


def extract_member_name_from_heading(heading: str) -> str:
    value = clean_html_text(heading)
    value = re.sub(r",\s*District\s+\d+.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^Council Vice-President\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^Council Vice President\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^Council President\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^City Council Member\s+", "", value, flags=re.IGNORECASE)
    return value.strip()


def extract_member_profiles(html: str, image_dir: Path, refresh_images: bool) -> list[dict[str, str]]:
    profiles: list[dict[str, str]] = []
    for portrait_url, heading, bio_url in CARD_RE.findall(html):
        name = extract_member_name_from_heading(heading)
        if not name:
            continue
        slug = slugify(name)
        portrait_path = (
            save_remote_image(normalize_url(portrait_url), image_dir, slug)
            if refresh_images
            else find_existing_image(image_dir, slug) or save_remote_image(normalize_url(portrait_url), image_dir, slug)
        )
        bio_page_url = normalize_url(bio_url)
        bio_page_html = fetch_text(bio_page_url)
        bio_match = BIO_RE.search(bio_page_html)
        biography = html_block_to_paragraph_text(bio_match.group(1)) if bio_match else ""
        biography = strip_contact_trailer(biography)
        profiles.append({
            "name": name,
            "portrait_path": portrait_path,
            "portrait_url": normalize_url(portrait_url),
            "bio_url": bio_page_url,
            "biography": biography,
        })
    return profiles


def match_profile_for_name(name: str, profiles: list[dict[str, str]]) -> dict[str, str] | None:
    if not name:
        return None
    candidates = set(person_name_candidates(name))
    if not candidates:
        return None
    for profile in profiles:
        profile_candidates = set(person_name_candidates(profile["name"]))
        if candidates & profile_candidates:
            return profile
    return None


def extract_meeting_context(html: str) -> dict[str, str]:
    return {
        "meeting_name": extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_hypName"),
        "meeting_date": extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_lblDate"),
        "meeting_time": extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_lblTime"),
        "meeting_location": extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_lblLocation"),
    }


def extract_legislation_links(html: str) -> list[dict[str, str]]:
    records: OrderedDict[str, dict[str, str]] = OrderedDict()
    for link in extract_links(html):
        if "LegislationDetail.aspx" not in link["url"]:
            continue
        record = records.setdefault(link["url"], {"detail_url": link["url"], "file_number": "", "title": ""})
        label = link["label"]
        if re.match(r"^[A-Z0-9-]+$", label):
            record["file_number"] = label
        elif label and not record["title"]:
            record["title"] = label
    return list(records.values())


def extract_attachments(html: str) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for link in extract_links(html):
        url = link["url"]
        if not any(token in url for token in ("View.ashx", ".pdf", ".doc", ".docx")):
            continue
        key = (link["label"], url)
        if key in seen:
            continue
        seen.add(key)
        label = link["label"]
        lowered = label.lower()
        if "testimony" in lowered:
            kind = "testimony"
        elif "comment" in lowered:
            kind = "comment"
        elif "agenda" in lowered:
            kind = "agenda"
        else:
            kind = "attachment"
        attachments.append({"name": label, "url": url, "kind": kind})
    return attachments


def extract_sponsors(html: str) -> list[str]:
    links = extract_links_from_element(html, "ctl00_ContentPlaceHolder1_lblSponsors2")
    if links:
        return [link["label"] for link in links]
    sponsors = extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_lblSponsors2")
    if not sponsors:
        return []
    return [part for part in (piece.strip() for piece in sponsors.split(",")) if part]


def extract_history(html: str) -> list[str]:
    history: list[str] = []
    for match in re.finditer(r"(Scheduled for a Public Hearing|Recommended Favorably|Approved|Failed|Withdrawn|Hearing Held)", html, re.IGNORECASE):
        value = clean_html_text(match.group(1))
        if value and value not in history:
            history.append(value)
    return history


def extract_type_from_url(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    matter_type = params.get("Type", [""])
    return matter_type[0]


def parse_legislation_detail(detail_url: str, html: str, meeting: dict[str, str]) -> dict[str, object]:
    file_number = extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_lblFile2") or meeting.get("file_number", "")
    title_text = extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_lblTitle2")
    title, summary = split_title_and_summary(title_text)
    sponsors = extract_sponsors(html)
    attachments = extract_links_from_element(html, "ctl00_ContentPlaceHolder1_lblAttachments2")
    attachments = [
        {
            "name": item["label"],
            "url": item["url"],
            "kind": ("testimony" if "testimony" in item["label"].lower()
                     else "comment" if "comment" in item["label"].lower()
                     else "attachment"),
        }
        for item in attachments
    ]
    testimony_attachments = [item for item in attachments if item["kind"] in {"testimony", "comment"}]
    history = extract_history(html)
    record_type = extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_lblType2") or extract_type_from_url(detail_url)
    committee = extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_hypInControlOf2") or meeting.get("meeting_name", "")
    status = extract_element_text_by_id(html, "ctl00_ContentPlaceHolder1_lblStatus2")

    categories = [value for value in [committee, record_type] if value]
    if testimony_attachments:
        categories.append("Has Testimony")

    return {
        "file_number": file_number,
        "title": title or extract_title(html),
        "summary": summary,
        "status": status or "Status unavailable",
        "type": record_type,
        "committee": committee,
        "meeting_name": meeting.get("meeting_name", ""),
        "meeting_date": meeting.get("meeting_date", ""),
        "meeting_time": meeting.get("meeting_time", ""),
        "meeting_location": meeting.get("meeting_location", ""),
        "meeting_url": meeting.get("meeting_url", ""),
        "detail_url": detail_url,
        "primary_sponsor": sponsors[0] if sponsors else "",
        "sponsors": sponsors,
        "categories": categories,
        "attachments": attachments,
        "testimony_attachments": testimony_attachments,
        "has_testimony": bool(testimony_attachments),
        "history": history,
        "latest_action": history[0] if history else "",
    }


def dedupe_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped: OrderedDict[str, dict[str, object]] = OrderedDict()
    for record in records:
        key = str(record.get("detail_url") or record.get("file_number") or record.get("title"))
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = record
            continue
        if not existing.get("testimony_attachments") and record.get("testimony_attachments"):
            existing["testimony_attachments"] = record["testimony_attachments"]
            existing["has_testimony"] = record["has_testimony"]
        if not existing.get("attachments") and record.get("attachments"):
            existing["attachments"] = record["attachments"]
        if not existing.get("meeting_date") and record.get("meeting_date"):
            existing["meeting_date"] = record["meeting_date"]
        if not existing.get("meeting_time") and record.get("meeting_time"):
            existing["meeting_time"] = record["meeting_time"]
        if not existing.get("meeting_location") and record.get("meeting_location"):
            existing["meeting_location"] = record["meeting_location"]
    return list(deduped.values())


def fetch_records(limit: int, image_dir: Path, refresh_images: bool) -> dict[str, object]:
    calendar_html = fetch_text(CALENDAR_URL)
    members_html = fetch_text(OFFICIAL_MEMBERS_URL)
    sponsor_profiles = extract_member_profiles(members_html, image_dir, refresh_images=refresh_images)
    meetings = extract_calendar_meetings(calendar_html)[:limit]
    records: list[dict[str, object]] = []

    for meeting in meetings:
        meeting_html = fetch_text(str(meeting["meeting_url"]))
        meeting_context = meeting | extract_meeting_context(meeting_html)
        legislation_links = extract_legislation_links(meeting_html)
        for legislation in legislation_links:
            detail_url = legislation["detail_url"]
            detail_html = fetch_text(detail_url)
            record = parse_legislation_detail(detail_url, detail_html, meeting_context | legislation)
            if record["title"] or record["file_number"]:
                primary_profile = match_profile_for_name(str(record.get("primary_sponsor", "")), sponsor_profiles)
                sponsor_profile_list = [
                    profile for sponsor_name in record.get("sponsors", [])
                    if (profile := match_profile_for_name(str(sponsor_name), sponsor_profiles))
                ]
                seen_profile_names: set[str] = set()
                deduped_profiles: list[dict[str, str]] = []
                for profile in sponsor_profile_list:
                    if profile["name"] in seen_profile_names:
                        continue
                    seen_profile_names.add(profile["name"])
                    deduped_profiles.append(profile)
                record["primary_sponsor_profile"] = primary_profile
                record["sponsor_profiles"] = deduped_profiles
                records.append(record)

    deduped = dedupe_records(records)
    return {
        "fetched_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_url": CALENDAR_URL,
        "member_source_url": OFFICIAL_MEMBERS_URL,
        "record_count": len(deduped),
        "sponsor_profiles": sponsor_profiles,
        "records": deduped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Cache Baltimore City Council testimony metadata to local file.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--limit-meetings",
        type=int,
        default=12,
        help="Maximum number of meeting detail pages to inspect from the public calendar (default: 12)",
    )
    parser.add_argument(
        "--refresh-profile-images",
        action="store_true",
        help="Force re-download of council member profile images instead of reusing cached local files",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        payload = fetch_records(
            limit=args.limit_meetings,
            image_dir=IMAGES_DIR,
            refresh_images=args.refresh_profile_images,
        )
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Failed to fetch Baltimore City Council testimony cache: {exc}") from exc

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {payload['record_count']} records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
