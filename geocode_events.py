import argparse
import os

from geocode_cache import load_geocode_cache, save_geocode_cache
from geocode_upcoming import geocode_upcoming_events


def parse_args():
    parser = argparse.ArgumentParser(
        description="Geocode events from an existing upcoming_events.json file."
    )
    parser.add_argument(
        "--city",
        default="baltimore",
        help="City name used for default paths (default: baltimore)",
    )
    parser.add_argument(
        "--events",
        dest="events_path",
        help="Path to the events JSON file (defaults to {city}/upcoming_events.json)",
    )
    parser.add_argument(
        "--cache",
        dest="cache_path",
        help="Path to the geocode cache file (defaults to {city}/geocode_cache.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not persist cache changes; useful for testing",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    events_path = args.events_path or os.path.join(args.city, "upcoming_events.json")
    cache_path = args.cache_path or os.path.join(args.city, "geocode_cache.json")

    geocode_cache = load_geocode_cache(cache_path)
    events, cache_updated = geocode_upcoming_events(
        args.city, geocode_cache, events_path=events_path, dry_run=args.dry_run
    )

    if events is None:
        raise SystemExit(1)

    if cache_updated and not args.dry_run:
        save_geocode_cache(geocode_cache, cache_path)
        print(f"Updated geocode cache written to {cache_path}.")
    elif cache_updated:
        print("Cache was updated, but --dry-run was specified; nothing written.")
    else:
        print("No cache updates were required.")


if __name__ == "__main__":
    main()
