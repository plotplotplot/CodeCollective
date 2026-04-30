#!/usr/bin/env python3
"""Build versioned, sharded Baltimore vacants datasets for R2 publishing."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


GROUPS = ("ALL", "VACANT_LOT", "VACANT_BUILDING_NOTICE")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shard Baltimore vacants GeoJSON into gzip pages.")
    parser.add_argument("--input", default="baltimore/data/vacants.geojson")
    parser.add_argument("--output-root", default="baltimore/data/publish")
    parser.add_argument("--prefix", default="vacants")
    parser.add_argument("--shard-size", type=int, default=1000)
    return parser.parse_args()


def load_payload(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Input must be a GeoJSON object")
    return payload


def write_gzip_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=6)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(compressed)
    return {"size_bytes": len(compressed), "sha256": hashlib.sha256(compressed).hexdigest()}


def select_group(features: list[dict[str, Any]], group: str) -> list[dict[str, Any]]:
    if group == "ALL":
        return features
    return [f for f in features if ((f.get("properties") or {}).get("_normalized") or {}).get("dataset") == group]


def iter_lon_lat_pairs(coords: Any):
    if not isinstance(coords, list) or not coords:
        return
    first = coords[0]
    if isinstance(first, (int, float)) and len(coords) >= 2:
        try:
            yield float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            return
        return
    for item in coords:
        yield from iter_lon_lat_pairs(item)


def feature_bounds(feature: dict[str, Any]) -> list[float] | None:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    points = list(iter_lon_lat_pairs(coords))
    if not points:
        return None
    lons = [pt[0] for pt in points]
    lats = [pt[1] for pt in points]
    return [min(lons), min(lats), max(lons), max(lats)]


def feature_lon_lat(feature: dict[str, Any]) -> tuple[float, float] | None:
    bounds = feature_bounds(feature)
    if not bounds:
        return None
    min_lon, min_lat, max_lon, max_lat = bounds
    return ((min_lon + max_lon) / 2.0, (min_lat + max_lat) / 2.0)


def spatial_sort_key(feature: dict[str, Any]) -> tuple[int, int, float, float]:
    lon_lat = feature_lon_lat(feature)
    if lon_lat is None:
        return (10**9, 10**9, 0.0, 0.0)
    lon, lat = lon_lat
    # Bucket features to keep nearby points in same shards.
    lat_bucket = int((lat + 90.0) * 100)
    lon_bucket = int((lon + 180.0) * 100)
    return (lat_bucket, lon_bucket, lat, lon)


def bbox_for_features(features: list[dict[str, Any]]) -> list[float] | None:
    min_lon: float | None = None
    min_lat: float | None = None
    max_lon: float | None = None
    max_lat: float | None = None
    for feature in features:
        bounds = feature_bounds(feature)
        if bounds is None:
            continue
        b_min_lon, b_min_lat, b_max_lon, b_max_lat = bounds
        min_lon = b_min_lon if min_lon is None else min(min_lon, b_min_lon)
        min_lat = b_min_lat if min_lat is None else min(min_lat, b_min_lat)
        max_lon = b_max_lon if max_lon is None else max(max_lon, b_max_lon)
        max_lat = b_max_lat if max_lat is None else max(max_lat, b_max_lat)
    if min_lon is None or min_lat is None or max_lon is None or max_lat is None:
        return None
    return [min_lon, min_lat, max_lon, max_lat]


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_root = Path(args.output_root).resolve()
    prefix = args.prefix.strip("/ ")
    if not prefix:
        raise ValueError("Prefix cannot be empty")
    if args.shard_size < 1:
        raise ValueError("Shard size must be >= 1")

    payload = load_payload(input_path)
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("Input payload missing features list")

    fetched_at = str(payload.get("fetched_at") or "").strip()
    version = datetime.now(UTC).strftime("v%Y%m%dT%H%M%SZ")

    manifest: dict[str, Any] = {
        "version": version,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_fetched_at": fetched_at,
        "source_feature_count": len(features),
        "shard_size": args.shard_size,
        "prefix": prefix,
        "groups": {},
    }

    for group in GROUPS:
        bucket = sorted(select_group(features, group), key=spatial_sort_key)
        page_count = math.ceil(len(bucket) / args.shard_size) if bucket else 0
        shards: list[dict[str, Any]] = []

        for page in range(1, page_count + 1):
            start = (page - 1) * args.shard_size
            end = start + args.shard_size
            batch = bucket[start:end]
            shard_payload = {
                "type": "FeatureCollection",
                "version": version,
                "group": group,
                "page": page,
                "page_size": args.shard_size,
                "total_features": len(bucket),
                "features": batch,
            }
            shard_key = f"{prefix}/{version}/shards/group={group}/page={page:04d}.json.gz"
            stats = write_gzip_json(output_root / shard_key, shard_payload)
            shards.append(
                {
                    "page": page,
                    "key": shard_key,
                    "count": len(batch),
                    "bbox": bbox_for_features(batch),
                    **stats,
                }
            )

        manifest["groups"][group] = {
            "count": len(bucket),
            "pages": page_count,
            "shards": shards,
        }

    manifest_key = f"{prefix}/{version}/manifest.json"
    latest_key = f"{prefix}/latest.json"
    latest_payload = {
        "version": version,
        "manifest_key": manifest_key,
        "generated_at": manifest["generated_at"],
        "source_fetched_at": fetched_at,
        "source_feature_count": len(features),
    }

    (output_root / manifest_key).parent.mkdir(parents=True, exist_ok=True)
    (output_root / manifest_key).write_text(json.dumps(manifest, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    (output_root / latest_key).write_text(json.dumps(latest_payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    print(json.dumps({"version": version, "output_root": str(output_root), "prefix": prefix, "feature_count": len(features)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
