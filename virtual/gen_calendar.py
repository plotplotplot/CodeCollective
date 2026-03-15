#!/usr/bin/env python3
import json
from pathlib import Path
import sys

CITY = "virtual"
CITY_DIR = Path(__file__).resolve().parent
ROOT_DIR = CITY_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import genSimpleCalendar

from scrape_ABWIPPM import scrape_events


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=4), encoding="utf-8")


def main():
    events = scrape_events()
    events.sort(key=lambda event: event.get("startDate", ""))

    write_json(CITY_DIR / "upcoming_events.json", events)
    write_json(CITY_DIR / "skipped_events.json", [])

    try:
        from genCalendar import events_to_ics

        events_to_ics(events, CITY, output_file=str(CITY_DIR / "cc_events.ics"))
    except Exception as exc:
        print(f"Skipping ICS generation: {exc}")

    print(f"Wrote {len(events)} event(s) for {CITY}")


if __name__ == "__main__":
    main()
