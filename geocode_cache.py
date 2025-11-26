import json
import os
from typing import Dict, Any

DEFAULT_CACHE_FILE = "geocode_cache.json"


def normalize_address(address: str) -> str:
    """Normalize address strings for consistent cache keys."""
    return address.strip().lower()


def load_geocode_cache(cache_file: str = None) -> Dict[str, Dict[str, float]]:
    """Load cached geocode lookups from disk."""
    cache_path = cache_file or DEFAULT_CACHE_FILE
    if not os.path.exists(cache_path):
        return {}

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k: {"latitude": float(v["latitude"]), "longitude": float(v["longitude"])} for k, v in data.items()}
    except (json.JSONDecodeError, OSError, KeyError, ValueError):
        return {}


def save_geocode_cache(cache: Dict[str, Dict[str, float]], cache_file: str = None) -> None:
    """Persist the geocode cache to disk."""
    cache_path = cache_file or DEFAULT_CACHE_FILE
    cache_dir = os.path.dirname(cache_path)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def apply_geocode_cache(events: Any, cache: Dict[str, Dict[str, float]]) -> bool:
    """
    Update events with cached coordinates and capture new coordinates into the cache.

    Returns:
        bool: True if the cache was updated and needs to be saved.
    """
    cache_updated = False

    for event in events:
        location = event.get("location") or {}
        if not location:
            continue

        address = location.get("address", "")
        if not address:
            continue

        key = normalize_address(address)
        if not key:
            continue

        lat = location.get("latitude")
        lon = location.get("longitude")

        if lat and lon:
            try:
                lat_val = float(lat)
                lon_val = float(lon)
            except (TypeError, ValueError):
                continue

            cached = cache.get(key)
            if not cached or cached.get("latitude") != lat_val or cached.get("longitude") != lon_val:
                cache[key] = {"latitude": lat_val, "longitude": lon_val}
                cache_updated = True
        else:
            cached = cache.get(key)
            if cached:
                location["latitude"] = cached["latitude"]
                location["longitude"] = cached["longitude"]
                event["location"] = location

    return cache_updated
