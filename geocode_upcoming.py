import json
import os

from geocode_cache import (
    normalize_address,
    is_low_quality_location,
    build_location_cache_keys,
    cache_entry_has_coordinates,
)
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def build_geocode_query(location_data, default_city=""):
    """Construct a geocoding query from the location metadata."""
    if not location_data:
        return ""

    address = (location_data.get("address") or "").strip()
    name = (location_data.get("name") or "").strip()
    city = (location_data.get("city") or "").strip()
    state = (location_data.get("state") or "").strip()
    postal_code = (location_data.get("postalCode") or "").strip()
    country = (location_data.get("country") or "").strip()
    default_city = (default_city or "").strip()

    if is_low_quality_location(address) and is_low_quality_location(name):
        return ""

    parts = []
    normalized_parts = []

    def append_part(value):
        trimmed = (value or "").strip()
        if not trimmed or is_low_quality_location(trimmed):
            return
        normalized = normalize_address(trimmed)
        if any(
            normalized == existing or normalized in existing or existing in normalized
            for existing in normalized_parts
        ):
            return
        parts.append(trimmed)
        normalized_parts.append(normalized)

    append_part(address)
    if not parts:
        append_part(name)

    for value in (city, state, postal_code, country):
        append_part(value)

    if not parts and name:
        append_part(name)

    append_part(default_city)
    return ", ".join(parts)


def geocode_upcoming_events(city, geocode_cache, events_path=None, dry_run=False, events=None):
    """Geocode events stored in upcoming_events.json for the provided city."""
    persist_to_disk = False
    if events is None:
        events_path = events_path or os.path.join(city, "upcoming_events.json")
        if not os.path.exists(events_path):
            print(f"No upcoming_events.json found for {city}; skipping geocoding")
            return None, False

        try:
            with open(events_path, "r", encoding="utf-8") as f:
                events = json.load(f)
        except Exception as exc:
            print(f"Unable to read events file for {city}: {exc}")
            return None, False
        persist_to_disk = True

    geolocator = Nominatim(user_agent="codecollective-calendar")
    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1,
        max_retries=2,
        error_wait_seconds=2.0,
        swallow_exceptions=True,
    )

    updated_events = 0
    cache_updated = False
    events_changed = False

    for event in events:
        location_data = event.get("location") or {}
        if not location_data:
            print(f"[geocode] Skipping '{event.get('name')}' – no location data present.")
            continue

        lat = location_data.get("latitude")
        lon = location_data.get("longitude")
        query = build_geocode_query(location_data, city)
        cache_keys = build_location_cache_keys(location_data, query=query)

        if lat not in (None, "") and lon not in (None, ""):
            try:
                lat_val = float(lat)
                lon_val = float(lon)
            except (TypeError, ValueError):
                print(f"[geocode] '{event.get('name')}' has invalid latitude/longitude values; skipping cache update.")
                continue

            location_data["latitude"] = lat_val
            location_data["longitude"] = lon_val
            location_data["geocode_status"] = "provided"
            if query:
                location_data["geocode_query"] = query
            event["location"] = location_data

            entry = {
                "latitude": lat_val,
                "longitude": lon_val,
                "status": "ok",
                "source": "provided",
            }
            for cache_key in cache_keys:
                cached = geocode_cache.get(cache_key)
                if cached != entry:
                    geocode_cache[cache_key] = dict(entry)
                    cache_updated = True
            print(f"[geocode] '{event.get('name')}' already has coordinates; updating cache if needed.")
            continue

        if not query:
            print(f"[geocode] Skipping '{event.get('name')}' – could not build geocode query from location data.")
            if location_data.get("geocode_status") != "skipped_low_quality":
                location_data["geocode_status"] = "skipped_low_quality"
                location_data.pop("geocode_query", None)
                event["location"] = location_data
                events_changed = True
            for cache_key in cache_keys:
                entry = geocode_cache.get(cache_key)
                negative_entry = {"status": "skipped_low_quality"}
                if entry != negative_entry:
                    geocode_cache[cache_key] = dict(negative_entry)
                    cache_updated = True
            continue

        coords = None
        cached_negative_status = ""
        for cache_key in cache_keys:
            entry = geocode_cache.get(cache_key)
            if not entry:
                continue
            if cache_entry_has_coordinates(entry):
                print(f"[geocode] Using cached coordinates for '{event.get('name')}'.")
                coords = entry
                break
            if entry.get("status") and entry.get("status") != "ok":
                cached_negative_status = entry["status"]

        if coords is None and cached_negative_status:
            print(f"[geocode] Skipping '{event.get('name')}' – cached status is {cached_negative_status}.")
            if location_data.get("geocode_status") != cached_negative_status or location_data.get("geocode_query") != query:
                location_data["geocode_status"] = cached_negative_status
                location_data["geocode_query"] = query
                event["location"] = location_data
                events_changed = True
            continue

        if coords is None:
            try:
                print(f"[geocode] Querying geocoder for '{event.get('name')}': {query}")
                result = geocode(query)
            except Exception as exc:
                print(f"[geocode] Geocoding failed for '{query}': {exc}")
                negative_entry = {
                    "status": "failed_error",
                    "error": str(exc)[:240],
                }
                for cache_key in cache_keys:
                    if geocode_cache.get(cache_key) != negative_entry:
                        geocode_cache[cache_key] = dict(negative_entry)
                        cache_updated = True
                if (
                    location_data.get("geocode_status") != "failed_error"
                    or location_data.get("geocode_query") != query
                ):
                    location_data["geocode_status"] = "failed_error"
                    location_data["geocode_query"] = query
                    event["location"] = location_data
                    events_changed = True
                continue
            if result:
                coords = {
                    "latitude": result.latitude,
                    "longitude": result.longitude,
                    "status": "ok",
                    "source": "nominatim",
                }
            else:
                print(f"[geocode] No geocode result returned for '{query}'.")

        if not coords:
            print(f"[geocode] Skipping '{event.get('name')}' – no coordinates available.")
            negative_entry = {"status": "failed_no_result"}
            for cache_key in cache_keys:
                if geocode_cache.get(cache_key) != negative_entry:
                    geocode_cache[cache_key] = dict(negative_entry)
                    cache_updated = True
            if location_data.get("geocode_status") != "failed_no_result" or location_data.get("geocode_query") != query:
                location_data["geocode_status"] = "failed_no_result"
                location_data["geocode_query"] = query
                event["location"] = location_data
                events_changed = True
            continue

        try:
            location_data["latitude"] = float(coords["latitude"])
            location_data["longitude"] = float(coords["longitude"])
        except (TypeError, ValueError, KeyError):
            continue

        location_data["geocode_status"] = "ok"
        location_data["geocode_query"] = query
        event["location"] = location_data
        updated_events += 1
        events_changed = True

        entry = {
            "latitude": location_data["latitude"],
            "longitude": location_data["longitude"],
            "status": "ok",
            "source": coords.get("source", "cache"),
        }
        for cache_key in cache_keys:
            if geocode_cache.get(cache_key) != entry:
                geocode_cache[cache_key] = dict(entry)
                cache_updated = True

    if dry_run:
        if updated_events:
            print(f"[dry-run] Would geocode {updated_events} event(s) for {city}.")
        elif events_changed:
            print(f"[dry-run] Would update geocode metadata for {city} without adding new coordinates.")
        else:
            print(f"[dry-run] No new geocoding data would be added for {city}.")
    else:
        if updated_events:
            if persist_to_disk:
                with open(events_path, "w", encoding="utf-8") as f:
                    json.dump(events, f, indent=4)
            print(f"Geocoded {updated_events} event(s) for {city}.")
        elif events_changed:
            if persist_to_disk:
                with open(events_path, "w", encoding="utf-8") as f:
                    json.dump(events, f, indent=4)
            print(f"Updated geocode metadata for {city} without adding new coordinates.")
        else:
            print(f"No new geocoding data added for {city}.")

    return events, cache_updated
