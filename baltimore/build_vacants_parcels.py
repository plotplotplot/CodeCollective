#!/usr/bin/env python3
"""Build parcel-boundary GeoJSON for Baltimore vacants using BLOCKLOT join."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

REALPROP_QUERY_API = "https://egisdata.baltimorecity.gov/egis/rest/services/Housing/Accela_DHCD/MapServer/1/query"


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_geojson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def chunked(values: list[str], size: int):
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


def query_parcels_for_blocklots(blocklots: list[str]) -> list[dict[str, Any]]:
    if not blocklots:
        return []
    quoted = ",".join(f"'{value.replace("'", "''")}'" for value in blocklots)
    params = {
        "where": f"BLOCKLOT IN ({quoted})",
        "outFields": "BLOCKLOT",
        "returnGeometry": "true",
        "f": "geojson",
        "outSR": "4326",
    }
    url = f"{REALPROP_QUERY_API}?{urlencode(params)}"
    with urlopen(url, timeout=180) as resp:
        payload = json.load(resp)
    return payload.get("features") or []


def main() -> int:
    parser = argparse.ArgumentParser(description="Build vacants parcel polygons from vacants points.")
    parser.add_argument("--vacants-input", default="baltimore/data/vacants.geojson")
    parser.add_argument("--output", default="baltimore/data/vacants_parcels.geojson")
    parser.add_argument("--batch-size", type=int, default=60)
    args = parser.parse_args()

    vacants = read_geojson(Path(args.vacants_input).resolve())
    features = vacants.get("features") or []

    by_group: dict[str, set[str]] = defaultdict(set)
    all_blocklots: set[str] = set()
    for feature in features:
        props = feature.get("properties") or {}
        normalized = props.get("_normalized") or {}
        dataset = str(normalized.get("dataset") or "ALL").strip() or "ALL"
        blocklot = str(normalized.get("blocklot") or props.get("BLOCKLOT") or "").strip()
        if not blocklot:
            continue
        by_group[dataset].add(blocklot)
        all_blocklots.add(blocklot)

    parcel_features: list[dict[str, Any]] = []
    parcel_by_blocklot: dict[str, list[dict[str, Any]]] = defaultdict(list)

    blocklots_sorted = sorted(all_blocklots)
    for batch in chunked(blocklots_sorted, max(1, args.batch_size)):
        for parcel in query_parcels_for_blocklots(batch):
            props = parcel.get("properties") or {}
            blocklot = str(props.get("BLOCKLOT") or "").strip()
            if not blocklot:
                continue
            parcel_by_blocklot[blocklot].append(parcel)

    for dataset, blocklots in by_group.items():
        for blocklot in sorted(blocklots):
            for parcel in parcel_by_blocklot.get(blocklot, []):
                props = dict(parcel.get("properties") or {})
                props["_normalized"] = {
                    "dataset": dataset,
                    "blocklot": blocklot,
                }
                parcel_features.append(
                    {
                        "type": "Feature",
                        "geometry": parcel.get("geometry"),
                        "properties": props,
                    }
                )

    payload = {
        "type": "FeatureCollection",
        "source": "Baltimore City Realprop layer joined to vacants by BLOCKLOT",
        "feature_count": len(parcel_features),
        "features": parcel_features,
    }
    write_geojson(Path(args.output).resolve(), payload)
    print(json.dumps({"output": args.output, "feature_count": len(parcel_features)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
