#!/usr/bin/env python3
"""Fetch and cache Maryland bills master list JSON for local/static use."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


def fetch_json(url: str, timeout: int = 60) -> list[dict]:
    req = Request(url, headers={"User-Agent": "CodeCollective-BillsCache/1.0"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310
        payload = resp.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("Expected top-level list from bills endpoint")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Cache Maryland bills JSON to local file.")
    parser.add_argument(
        "--session",
        default="2026rs",
        help="Session slug used by MGA endpoint (default: 2026rs)",
    )
    parser.add_argument(
        "--output",
        default="data/maryland_bills_2026.json",
        help="Output JSON path (default: data/maryland_bills_2026.json)",
    )
    args = parser.parse_args()

    url = f"https://mgaleg.maryland.gov/{args.session}/misc/billsmasterlist/legislation.json"
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        bills = fetch_json(url)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Failed to fetch bills cache from {url}: {exc}") from exc

    output_path.write_text(json.dumps(bills, indent=2), encoding="utf-8")
    print(f"Wrote {len(bills)} bills to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
