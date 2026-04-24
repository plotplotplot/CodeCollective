import json
import os
import shutil


def write_json(path, payload, description):
    with open(path, "w+", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    print(f"{description} saved to {path}")


def persist_calendar_outputs(
    city,
    sorted_events,
    invalid_events,
    scrape_errors,
    events_to_ics,
):
    write_json(os.path.join(city, "upcoming_events.json"), sorted_events, "Upcoming events")
    write_json(os.path.join(city, "skipped_events.json"), invalid_events, "Skipped events")

    scrape_errors_path = os.path.join(city, "scrape_errors.json")
    with open(scrape_errors_path, "w+", encoding="utf-8") as f:
        json.dump(scrape_errors, f, indent=4)
    if scrape_errors:
        print(f"Scrape errors saved to {scrape_errors_path}")

    events_to_ics(sorted_events, city, output_file=os.path.join(city, "cc_events.ics"))
    if city == "baltimore":
        shutil.copy2(os.path.join(city, "cc_events.ics"), "cc_events.ics")
        shutil.copy2(os.path.join(city, "upcoming_events.json"), "upcoming_events.json")
