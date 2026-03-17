#!/usr/bin/env python3
"""Fetch and cache Maryland MGA hearing schedule / witness signup metadata."""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag


BASE_URL = "https://mgaleg.maryland.gov"
DAY_URL = f"{BASE_URL}/mgawebsite/Meetings/Day"
REFRESH_DAY_URL = f"{BASE_URL}/mgawebsite/Meetings/RefreshDay"
DEFAULT_BILLS_INPUT = Path("data/maryland_bills_2026.json")
DEFAULT_OUTPUT = Path("data/maryland_bill_hearings_2026.json")
USER_AGENT = "CodeCollective-MDBillsHearingsCache/1.0"
HEARING_FIELDS = (
    "HearingDateTimePrimaryHouseOfOrigin",
    "HearingDateTimeSecondaryHouseOfOrigin",
    "HearingDateTimePrimaryOppositeHouse",
    "HearingDateTimeSecondaryOppositeHouse",
)


@dataclass
class HearingEntry:
    hearing_date: str
    committee_name: str
    hearing_title: str
    hearing_time_label: str
    hearing_day_url: str
    witness_signup_url: str


def load_bills(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
      raise ValueError(f"Expected a list in {path}")
    return data


def collect_hearing_dates(bills: list[dict]) -> list[str]:
    dates: set[str] = set()
    for bill in bills:
        for field in HEARING_FIELDS:
            value = bill.get(field)
            if not value:
                continue
            try:
                parsed = datetime.fromisoformat(str(value))
            except ValueError:
                continue
            dates.add(parsed.strftime("%m/%d/%Y"))
    return sorted(dates, key=lambda value: datetime.strptime(value, "%m/%d/%Y"))


def fetch_day_html(session: requests.Session, hearing_date: str, year: str) -> str:
    session.get(DAY_URL, timeout=60)
    response = session.post(
        REFRESH_DAY_URL,
        data={
            "ys": f"{year}rs",
            "cmte": "allcommittees",
            "includeBudget": "show",
            "showUpdates": "show",
            "Years": year,
            "dateType": "day",
            "hearingDateDay": hearing_date,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.text


def normalize_bill_number(value: str) -> str:
    return str(value or "").strip().upper()


def extract_bill_numbers(container: Tag) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for link in container.select('a[href*="/mgawebsite/Legislation/Details/"]'):
        bill_number = normalize_bill_number(link.get_text(" ", strip=True))
        if bill_number and bill_number not in seen:
            out.append(bill_number)
            seen.add(bill_number)
    return out


def absolute_url(value: str) -> str:
    return urljoin(BASE_URL, value)


def extract_hearing_time_label(header: Tag) -> str:
    for block in header.select(".font-weight-bold.text-center"):
        text = " ".join(block.stripped_strings)
        if ":" in text and ("AM" in text or "PM" in text):
            return text
    return ""


def extract_hearing_title(header: Tag) -> str:
    blocks = header.select(".font-weight-bold.text-center")
    if not blocks:
        return ""
    return " ".join(blocks[0].stripped_strings)


def extract_witness_signup_url(header: Tag) -> str:
    link = header.select_one('a[aria-label*="Witness Sign up"]')
    if not link or not link.get("href"):
        return ""
    return absolute_url(str(link["href"]))


def extract_hearing_date_from_signup(url: str, fallback_date: str) -> str:
    if not url:
        return fallback_date
    parsed = urlparse(url)
    hearing_date = parse_qs(parsed.query).get("hearingDate", [""])[0]
    return unquote(hearing_date) or fallback_date


def parse_schedule_page(html: str, fallback_date: str) -> dict[str, list[HearingEntry]]:
    soup = BeautifulSoup(html, "html.parser")
    all_hearings = soup.find(id="divAllHearings")
    if not all_hearings:
        return {}

    by_bill: dict[str, list[HearingEntry]] = defaultdict(list)
    current_committee = ""
    current_header: Tag | None = None

    for child in all_hearings.find_all(recursive=False):
        if not isinstance(child, Tag):
            continue

        classes = set(child.get("class", []))
        committee_banner = child if "hearsched-committee-banner" in classes else child.select_one(".hearsched-committee-banner")
        if committee_banner:
            current_committee = " ".join(committee_banner.stripped_strings)
            continue

        hearing_header = child if "hearsched-hearing-header" in classes else child.select_one(".hearsched-hearing-header")
        if hearing_header:
            current_header = hearing_header
            continue

        if child.name == "hr":
            current_header = None
            continue

        if current_header is None:
            continue

        bill_numbers = extract_bill_numbers(child)
        if not bill_numbers:
            continue

        witness_signup_url = extract_witness_signup_url(current_header)
        hearing_date = extract_hearing_date_from_signup(witness_signup_url, fallback_date)
        hearing_title = extract_hearing_title(current_header)
        hearing_time_label = extract_hearing_time_label(current_header)

        entry = HearingEntry(
            hearing_date=hearing_date,
            committee_name=current_committee,
            hearing_title=hearing_title,
            hearing_time_label=hearing_time_label,
            hearing_day_url=DAY_URL,
            witness_signup_url=witness_signup_url,
        )
        for bill_number in bill_numbers:
            by_bill[bill_number].append(entry)

    return by_bill


def dedupe_entries(entries: list[HearingEntry]) -> list[HearingEntry]:
    seen: set[tuple[str, str, str, str, str]] = set()
    out: list[HearingEntry] = []
    for entry in entries:
        key = (
            entry.hearing_date,
            entry.committee_name,
            entry.hearing_title,
            entry.hearing_time_label,
            entry.witness_signup_url,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def build_output(
    bills: list[dict],
    by_bill: dict[str, list[HearingEntry]],
    session_slug: str,
) -> dict:
    records: dict[str, dict] = {}
    for bill in bills:
        bill_number = normalize_bill_number(bill.get("BillNumber", ""))
        if not bill_number:
            continue
        entries = dedupe_entries(by_bill.get(bill_number, []))
        hearing_day_url = f"{BASE_URL}/mgawebsite/Meetings/Day/{bill_number}"
        testimony_url = next((entry.witness_signup_url for entry in entries if entry.witness_signup_url), "")
        records[bill_number] = {
            "bill_number": bill_number,
            "hearing_day_url": hearing_day_url,
            "testify_url": testimony_url or hearing_day_url,
            "has_testify_signup": bool(testimony_url),
            "hearings": [asdict(entry) for entry in entries],
        }
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "session": session_slug.upper(),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Cache MGA hearing schedule / witness signup metadata.")
    parser.add_argument("--bills-input", default=str(DEFAULT_BILLS_INPUT), help="Path to Maryland bills JSON cache.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path.")
    parser.add_argument("--session", default="2026rs", help="Session slug, e.g. 2026rs.")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between hearing-date requests.")
    parser.add_argument("--limit-dates", type=int, default=0, help="Optional max number of dates to scrape for testing.")
    parser.add_argument("--only-date", default="", help="Optional single hearing date in MM/DD/YYYY for targeted testing.")
    args = parser.parse_args()

    bills = load_bills(Path(args.bills_input))
    hearing_dates = collect_hearing_dates(bills)
    if args.only_date:
        hearing_dates = [args.only_date]
    if args.limit_dates > 0:
        hearing_dates = hearing_dates[:args.limit_dates]

    session_year = args.session[:4]
    http = requests.Session()
    http.headers.update({"User-Agent": USER_AGENT})

    merged: dict[str, list[HearingEntry]] = defaultdict(list)
    for idx, hearing_date in enumerate(hearing_dates, start=1):
        html = fetch_day_html(http, hearing_date, session_year)
        parsed = parse_schedule_page(html, hearing_date)
        for bill_number, entries in parsed.items():
            merged[bill_number].extend(entries)
        print(f"[{idx}/{len(hearing_dates)}] scraped {hearing_date} -> {sum(len(v) for v in parsed.values())} bill hearing entries")
        if args.delay:
            time.sleep(args.delay)

    output = build_output(bills, merged, args.session)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote hearing/testimony cache for {len(output['records'])} bills to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
