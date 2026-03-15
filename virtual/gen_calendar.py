#!/usr/bin/env python3
import importlib
import json
from pathlib import Path
import sys

CITY = "virtual"
CITY_DIR = Path(__file__).resolve().parent
ROOT_DIR = CITY_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import genSimpleCalendar

def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=4), encoding="utf-8")


def collect_events(city=CITY, error_logger=None):
    new_events = []

    try:
        scrape_abwippm = importlib.import_module("virtual.scrape_ABWIPPM")
        new_events += scrape_abwippm.scrape_events()
    except Exception as exc:
        print(f"Skipping ABWIPPM events: {exc}")
        if error_logger:
            error_logger("city_collect", exc, scraper="virtual.scrape_ABWIPPM")

    try:
        scrape_water_is_life = importlib.import_module("virtual.scrape_water_is_life")
        new_events += scrape_water_is_life.scrape_events()
    except Exception as exc:
        print(f"Skipping Water Is Life events: {exc}")
        if error_logger:
            error_logger("city_collect", exc, scraper="virtual.scrape_water_is_life")

    return new_events


def main():
    events = collect_events()
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
