#!/usr/bin/env python3
"""Fetch and cache Maryland MGA roll-call vote metadata by bill."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


BASE_URL = "https://mgaleg.maryland.gov"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/mgawebsite/Legislation/Details/{{bill_number}}?ys={{session_slug}}"
DEFAULT_BILLS_INPUT = Path("data/maryland_bills_2026.json")
DEFAULT_OUTPUT = Path("data/maryland_bill_votes_2026.json")
USER_AGENT = "CodeCollective-MDBillsVotesCache/1.0"

SECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"Voting\s+Yea\s*-\s*\d+", "Yea"),
    (r"Voting\s+Nay\s*-\s*\d+", "Nay"),
    (r"Not\s+Voting\s*-\s*\d+", "Not Voting"),
    (r"Excused\s+from\s+Voting\s*-\s*\d+", "Excused"),
    (r"Excused\s+\(Absent\)\s*-\s*\d+", "Absent"),
)

KNOWN_COMPOUND_SURNAMES: set[tuple[str, str]] = {
    ("Palakovich", "Carr"),
    ("White", "Holland"),
}


@dataclass
class VoteEvent:
    pdf_url: str
    vote_scope: str
    chamber: str
    seq_no: str
    calendar_date: str
    legislative_date: str
    counts: dict[str, int]
    member_votes: dict[str, str]


def load_bills(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list in {path}")
    return payload


def normalize_bill_number(value: str) -> str:
    return str(value or "").strip().upper()


def normalize_member_token(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def infer_scope_from_url(pdf_url: str) -> str:
    lowered = pdf_url.lower()
    if "/votes_comm/" in lowered:
        return "committee"
    if "/votes/" in lowered:
        return "floor"
    return "unknown"


def infer_chamber_from_url(pdf_url: str) -> str:
    lowered = pdf_url.lower()
    if "/votes/house/" in lowered:
        return "house"
    if "/votes/senate/" in lowered:
        return "senate"
    return ""


def find_vote_links(detail_html: str, session_slug: str) -> list[str]:
    soup = BeautifulSoup(detail_html, "html.parser")
    out: list[str] = []
    seen: set[str] = set()
    session_prefix = f"/{session_slug.upper()}/"
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "")
        if not href.lower().endswith(".pdf"):
            continue
        if "/votes/" not in href.lower() and "/votes_comm/" not in href.lower():
            continue
        if session_prefix not in href.upper():
            continue
        absolute = urljoin(BASE_URL, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append(absolute)
    return out


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    text_parts: list[str] = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def parse_vote_counts(text: str) -> dict[str, int]:
    match = re.search(
        r"(\d+)\s+Yeas\s+(\d+)\s+Nays\s+(\d+)\s+Not\s+Voting\s+(\d+)\s+Excused\s+(\d+)\s+Absent",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return {}
    return {
        "yeas": int(match.group(1)),
        "nays": int(match.group(2)),
        "not_voting": int(match.group(3)),
        "excused": int(match.group(4)),
        "absent": int(match.group(5)),
    }


def parse_member_votes(text: str) -> dict[str, str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    member_votes: dict[str, str] = {}

    section_indices: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        for pattern, label in SECTION_PATTERNS:
            if re.fullmatch(pattern, line, flags=re.IGNORECASE):
                section_indices.append((idx, label))
                break

    if not section_indices:
        return member_votes

    section_indices.append((len(lines), ""))
    ignore_tokens = {
        "Voting",
        "Yea",
        "Nay",
        "Not",
        "Excused",
        "Absent",
        "Vote",
        "Change",
        "Indicates",
    }
    initial_pattern = re.compile(r"^[A-Z]\.$")

    for i in range(len(section_indices) - 1):
        start_idx, label = section_indices[i]
        end_idx, _ = section_indices[i + 1]
        for line in lines[start_idx + 1:end_idx]:
            if line.startswith("* Indicates"):
                break
            tokens = line.split()
            cursor = 0
            while cursor < len(tokens):
                token = tokens[cursor]
                if token in ignore_tokens:
                    cursor += 1
                    continue
                if not re.fullmatch(r"[A-Z][A-Za-z'.-]*,?", token):
                    cursor += 1
                    continue

                name = token
                if token.endswith(",") and cursor + 1 < len(tokens) and initial_pattern.fullmatch(tokens[cursor + 1]):
                    name = f"{token} {tokens[cursor + 1]}"
                    cursor += 1
                elif cursor + 1 < len(tokens) and (token, tokens[cursor + 1]) in KNOWN_COMPOUND_SURNAMES:
                    name = f"{token} {tokens[cursor + 1]}"
                    cursor += 1

                name = normalize_member_token(name)
                if not name or name in ignore_tokens:
                    cursor += 1
                    continue
                if all(part in ignore_tokens for part in name.split()):
                    cursor += 1
                    continue
                member_votes[name] = label
                cursor += 1

    return member_votes


def parse_vote_event(pdf_url: str, pdf_text: str) -> VoteEvent:
    seq_match = re.search(r"SEQ NO\.\s*([0-9]+)", pdf_text, flags=re.IGNORECASE)
    cal_match = re.search(r"Calendar Date:\s*([^\n]+)", pdf_text, flags=re.IGNORECASE)
    leg_match = re.search(r"Legislative Date:\s*([^\n]+)", pdf_text, flags=re.IGNORECASE)
    return VoteEvent(
        pdf_url=pdf_url,
        vote_scope=infer_scope_from_url(pdf_url),
        chamber=infer_chamber_from_url(pdf_url),
        seq_no=(seq_match.group(1).strip() if seq_match else ""),
        calendar_date=(cal_match.group(1).strip() if cal_match else ""),
        legislative_date=(leg_match.group(1).strip() if leg_match else ""),
        counts=parse_vote_counts(pdf_text),
        member_votes=parse_member_votes(pdf_text),
    )


def fetch_with_retry(session: requests.Session, url: str, timeout: int = 60, retries: int = 2) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:  # pragma: no cover - network behavior
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"unreachable retry branch for {url}") from last_error


def build_output(
    session_slug: str,
    records: dict[str, dict],
    detail_failures: list[dict],
    pdf_failures: list[dict],
) -> dict:
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "session": session_slug.upper(),
        "source": "https://mgaleg.maryland.gov/mgawebsite/Legislation/Details",
        "count": len(records),
        "detail_failures": detail_failures,
        "pdf_failures": pdf_failures,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Cache MGA vote metadata by bill.")
    parser.add_argument("--bills-input", default=str(DEFAULT_BILLS_INPUT), help="Path to bills cache JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path.")
    parser.add_argument("--session", default="2026RS", help="Session slug, e.g. 2026RS.")
    parser.add_argument("--delay", type=float, default=0.02, help="Delay between bill-detail requests.")
    parser.add_argument("--limit", type=int, default=0, help="Optional bill limit for testing.")
    args = parser.parse_args()

    bills = load_bills(Path(args.bills_input))
    bill_numbers = [normalize_bill_number(bill.get("BillNumber")) for bill in bills]
    bill_numbers = [bill for bill in bill_numbers if bill]
    if args.limit > 0:
        bill_numbers = bill_numbers[:args.limit]

    session_slug = str(args.session).upper()
    http = requests.Session()
    http.headers.update({"User-Agent": USER_AGENT})

    parsed_pdf_cache: dict[str, VoteEvent] = {}
    records: dict[str, dict] = {}
    detail_failures: list[dict] = []
    pdf_failures: list[dict] = []

    for idx, bill_number in enumerate(bill_numbers, start=1):
        detail_url = DETAIL_URL_TEMPLATE.format(
            bill_number=quote(bill_number, safe=""),
            session_slug=quote(session_slug, safe=""),
        )
        try:
            detail_resp = fetch_with_retry(http, detail_url, timeout=60, retries=2)
        except requests.RequestException as exc:
            detail_failures.append({"bill_number": bill_number, "detail_url": detail_url, "error": str(exc)})
            print(f"[{idx}/{len(bill_numbers)}] {bill_number} detail fetch failed")
            continue

        vote_links = find_vote_links(detail_resp.text, session_slug=session_slug)
        events: list[VoteEvent] = []

        for pdf_url in vote_links:
            if pdf_url in parsed_pdf_cache:
                events.append(parsed_pdf_cache[pdf_url])
                continue
            try:
                pdf_resp = fetch_with_retry(http, pdf_url, timeout=60, retries=2)
                pdf_text = extract_pdf_text(pdf_resp.content)
                event = parse_vote_event(pdf_url, pdf_text)
                parsed_pdf_cache[pdf_url] = event
                events.append(event)
            except Exception as exc:  # noqa: BLE001
                pdf_failures.append({"bill_number": bill_number, "pdf_url": pdf_url, "error": str(exc)})

        if events:
            latest_member_votes = events[-1].member_votes
            records[bill_number] = {
                "bill_number": bill_number,
                "detail_url": detail_url,
                "vote_links": vote_links,
                "events": [asdict(event) for event in events],
                "latest_member_votes": latest_member_votes,
            }

        print(f"[{idx}/{len(bill_numbers)}] {bill_number} -> {len(vote_links)} vote PDFs ({len(events)} parsed)")
        if args.delay > 0:
            time.sleep(args.delay)

    output = build_output(
        session_slug=session_slug,
        records=records,
        detail_failures=detail_failures,
        pdf_failures=pdf_failures,
    )
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} bill vote records to {out_path}")
    print(f"Detail failures: {len(detail_failures)} | PDF failures: {len(pdf_failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
