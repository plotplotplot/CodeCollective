#!/usr/bin/env python3
"""Fetch Baltimore vacant-property datasets (vacant lots + vacant building notices)."""

from __future__ import annotations

import argparse
import gzip
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

BASE = "https://egisdata.baltimorecity.gov/egis/rest/services/Housing/Accela_DHCD/MapServer"
LAYERS = {
    "VACANT_LOT": 8,
    "VACANT_BUILDING_NOTICE": 9,
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_count(layer_id: int) -> int:
    query = urlencode({"where": "1=1", "returnCountOnly": "true", "f": "pjson"})
    with urlopen(f"{BASE}/{layer_id}/query?{query}", timeout=120) as resp:
        payload = json.load(resp)
    return int(payload.get("count") or 0)


def fetch_page(layer_id: int, offset: int, page_size: int) -> dict[str, Any]:
    query = urlencode(
        {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
            "orderByFields": "OBJECTID",
        }
    )
    with urlopen(f"{BASE}/{layer_id}/query?{query}", timeout=180) as resp:
        return json.load(resp)


def to_iso_maybe_epoch(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        epoch_ms = int(value)
    except (TypeError, ValueError):
        return str(value)
    return datetime.fromtimestamp(epoch_ms / 1000, tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_feature(feature: dict[str, Any], dataset: str) -> dict[str, Any]:
    props = dict(feature.get("properties") or {})
    # Keep raw and add normalized fields for map popups/filtering.
    normalized = {
        "dataset": dataset,
        "address": str(props.get("Address") or props.get("FULLADDR") or "").strip(),
        "neighborhood": str(props.get("Neighborhood") or props.get("NEIGHBOR") or "").strip(),
        "blocklot": str(props.get("BLOCKLOT") or "").strip(),
        "owner": str(props.get("OWNER_ABBR") or props.get("OWNER_1") or "").strip(),
        "notice_number": str(props.get("NoticeNum") or "").strip(),
        "date_notice": to_iso_maybe_epoch(props.get("DateNotice")),
        "date_cancel": to_iso_maybe_epoch(props.get("DateCancel")),
        "date_abate": to_iso_maybe_epoch(props.get("DateAbate")),
    }
    props["_normalized"] = normalized
    return {
        "type": "Feature",
        "geometry": feature.get("geometry"),
        "properties": props,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_json_gz(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Baltimore vacant-property layers as GeoJSON.")
    parser.add_argument("--output", default="baltimore/data/vacants.geojson")
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    page_size = max(100, min(args.page_size, 2000))

    all_features: list[dict[str, Any]] = []
    sources: dict[str, Any] = {}

    for dataset, layer_id in LAYERS.items():
        count = fetch_count(layer_id)
        fetched = 0
        layer_features: list[dict[str, Any]] = []
        while fetched < count:
            page = fetch_page(layer_id, fetched, page_size)
            features = page.get("features") or []
            if not features:
                break
            for feature in features:
                layer_features.append(normalize_feature(feature, dataset))
            fetched += len(features)

        all_features.extend(layer_features)
        sources[dataset] = {
            "layer_id": layer_id,
            "record_count": len(layer_features),
            "service_url": f"{BASE}/{layer_id}",
        }

    payload = {
        "type": "FeatureCollection",
        "fetched_at": utc_now(),
        "city": "baltimore",
        "source": "Baltimore City Housing Accela_DHCD MapServer",
        "sources": sources,
        "feature_count": len(all_features),
        "features": all_features,
    }

    write_json(output_path, payload)
    write_json_gz(Path(f"{output_path}.gz"), payload)
    print(json.dumps({"output": str(output_path), "feature_count": len(all_features), "sources": sources}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
