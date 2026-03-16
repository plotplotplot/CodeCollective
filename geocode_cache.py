import json
import os
import re
import unicodedata
from typing import Dict, Any, Iterable, List

DEFAULT_CACHE_FILE = "geocode_cache.json"
LOW_QUALITY_LOCATION_VALUES = {
    "",
    "united states",
    "usa",
    "us",
    "virtual",
    "virtual event",
    "online",
    "online event",
    "off-site",
    "off site",
    "remote",
    "tbd",
    "to be announced",
    "to be determined",
}


def normalize_address(address: str) -> str:
    """Normalize address strings for consistent cache keys."""
    text = unicodedata.normalize("NFKC", str(address or ""))
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    return text


def is_low_quality_location(value: str) -> bool:
    normalized = normalize_address(value)
    if normalized in LOW_QUALITY_LOCATION_VALUES:
        return True
    if len(normalized) < 8:
        return True
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return True
    return False


def cache_entry_has_coordinates(entry: Dict[str, Any]) -> bool:
    if not isinstance(entry, dict):
        return False
    try:
        float(entry["latitude"])
        float(entry["longitude"])
        return True
    except (KeyError, TypeError, ValueError):
        return False


def build_location_cache_keys(location_data: Dict[str, Any], query: str = "") -> List[str]:
    values: List[str] = []
    if isinstance(location_data, dict):
        for key in ("address", "name"):
            value = location_data.get(key)
            if value:
                values.append(value)
    if query:
        values.append(query)

    keys = []
    seen = set()
    for value in values:
        normalized = normalize_address(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        keys.append(normalized)
    return keys


def load_geocode_cache(cache_file: str = None) -> Dict[str, Dict[str, Any]]:
    """Load cached geocode lookups from disk."""
    cache_path = cache_file or DEFAULT_CACHE_FILE
    if not os.path.exists(cache_path):
        return {}

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            normalized_cache = {}
            for key, value in data.items():
                if not isinstance(value, dict):
                    continue
                entry = dict(value)
                if cache_entry_has_coordinates(entry):
                    entry["latitude"] = float(entry["latitude"])
                    entry["longitude"] = float(entry["longitude"])
                    entry.setdefault("status", "ok")
                normalized_cache[normalize_address(key)] = entry
            return normalized_cache
    except (json.JSONDecodeError, OSError, KeyError, ValueError):
        return {}


def save_geocode_cache(cache: Dict[str, Dict[str, Any]], cache_file: str = None) -> None:
    """Persist the geocode cache to disk."""
    cache_path = cache_file or DEFAULT_CACHE_FILE
    cache_dir = os.path.dirname(cache_path)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def apply_geocode_cache(events: Any, cache: Dict[str, Dict[str, Any]]) -> bool:
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

        cache_keys = build_location_cache_keys(location)
        if not cache_keys:
            continue

        lat = location.get("latitude")
        lon = location.get("longitude")

        if lat not in (None, "") and lon not in (None, ""):
            try:
                lat_val = float(lat)
                lon_val = float(lon)
            except (TypeError, ValueError):
                continue

            entry = {"latitude": lat_val, "longitude": lon_val, "status": "ok"}
            for key in cache_keys:
                cached = cache.get(key)
                if cached != entry:
                    cache[key] = dict(entry)
                    cache_updated = True
        else:
            cached = None
            for key in cache_keys:
                entry = cache.get(key)
                if cache_entry_has_coordinates(entry):
                    cached = entry
                    break
            if cached:
                location["latitude"] = cached["latitude"]
                location["longitude"] = cached["longitude"]
                location.setdefault("geocode_status", cached.get("status", "ok"))
                event["location"] = location

    return cache_updated
