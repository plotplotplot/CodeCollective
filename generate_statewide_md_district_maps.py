#!/usr/bin/env python3
"""Generate standardized full-Maryland district maps from official polygon data.

This pipeline renders vector polygons from Maryland's official election boundaries
service so each output image uses the same statewide frame and outline.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
from PIL import Image
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import unary_union
import requests

FEATURE_URL = (
    "https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/"
    "FeatureServer/1/query?where=1%3D1&outFields=DISTRICT&returnGeometry=true&f=geojson"
)


def ensure_geojson(cache_path: Path, refresh: bool = False) -> dict[str, Any]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if not refresh and cache_path.exists() and cache_path.stat().st_size > 0:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    resp = requests.get(FEATURE_URL, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    cache_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def parse_district_label(value: str) -> str:
    text = str(value or "").strip().upper()
    m = re.match(r"^0*(\d{1,2})([A-Z]?)$", text)
    if not m:
        return ""
    return f"{int(m.group(1)):02d}{m.group(2)}"


def polygon_parts(geom: Polygon | MultiPolygon) -> list[Polygon]:
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return []


def add_geom_patch(ax: plt.Axes, geom: Polygon | MultiPolygon, *, facecolor: str, edgecolor: str, linewidth: float, alpha: float) -> None:
    for part in polygon_parts(geom):
        coords = list(part.exterior.coords)
        if len(coords) < 3:
            continue
        ax.add_patch(
            MplPolygon(
                coords,
                closed=True,
                facecolor=facecolor,
                edgecolor=edgecolor,
                linewidth=linewidth,
                alpha=alpha,
                joinstyle="round",
            )
        )


def draw_district_image(
    out_path: Path,
    district_label: str,
    district_geoms: dict[str, Polygon | MultiPolygon],
    state_geom: Polygon | MultiPolygon,
) -> bool:
    normalized = parse_district_label(district_label)
    if not normalized:
        return False

    selected = district_geoms.get(normalized)
    if selected is None:
        prefix = normalized[:2]
        matches = [geom for key, geom in district_geoms.items() if key.startswith(prefix)]
        if not matches:
            return False
        selected = unary_union(matches)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor((0, 0, 0, 0))

    add_geom_patch(
        ax,
        state_geom,
        facecolor="#eef2f4",
        edgecolor="#b7c2cc",
        linewidth=1.0,
        alpha=1.0,
    )

    for key, geom in district_geoms.items():
        if key == normalized:
            continue
        add_geom_patch(
            ax,
            geom,
            facecolor="#dfe8ef",
            edgecolor="#d7e0e8",
            linewidth=0.45,
            alpha=1.0,
        )

    add_geom_patch(
        ax,
        selected,
        facecolor="#c6dc52",
        edgecolor="#7e9524",
        linewidth=1.35,
        alpha=1.0,
    )

    minx, miny, maxx, maxy = state_geom.bounds
    dx = maxx - minx
    dy = maxy - miny
    padx = dx * 0.06
    pady = dy * 0.06
    ax.set_xlim(minx - padx, maxx + padx)
    ax.set_ylim(miny - pady, maxy + pady)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(
        0.02,
        0.98,
        f"District {normalized}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=22,
        fontweight="bold",
        color="#13253f",
        bbox={"facecolor": "#ffffff", "edgecolor": "#c5d0da", "boxstyle": "round,pad=0.3", "alpha": 0.9},
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    Image.fromarray(rgba, mode="RGBA").save(
        out_path,
        format="WEBP",
        lossless=True,
        quality=85,
        method=6,
    )
    plt.close(fig)
    return True


def build_district_geometries(payload: dict[str, Any]) -> dict[str, Polygon | MultiPolygon]:
    grouped: dict[str, list[Polygon | MultiPolygon]] = defaultdict(list)
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        key = parse_district_label(props.get("DISTRICT", ""))
        geom_json = feature.get("geometry")
        if not key or not geom_json:
            continue
        grouped[key].append(shape(geom_json))
    return {key: unary_union(geoms) for key, geoms in grouped.items() if geoms}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate statewide Maryland district context maps.")
    parser.add_argument("--input-json", default="data/mga_sponsors_2026.json")
    parser.add_argument("--geojson-cache", default="data/md_legislative_districts_2022.geojson")
    parser.add_argument("--district-image-dir", default="images/md_district_statewide")
    parser.add_argument("--output-dir", default="images/politicians_standardized")
    parser.add_argument("--refresh-geojson", action="store_true")
    parser.add_argument("--write-json", action="store_true")
    args = parser.parse_args()

    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = payload.get("records", [])
    if not records:
        raise SystemExit("No sponsor records found.")

    districts_payload = ensure_geojson(Path(args.geojson_cache), refresh=args.refresh_geojson)
    district_geoms = build_district_geometries(districts_payload)
    if not district_geoms:
        raise SystemExit("No district geometries found in geojson payload.")
    state_geom = unary_union(list(district_geoms.values()))

    district_dir = Path(args.district_image_dir)
    output_dir = Path(args.output_dir)
    district_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    unique_labels = {
        parse_district_label(rec.get("district", ""))
        for rec in records
        if parse_district_label(rec.get("district", ""))
    }
    rendered_base = 0
    district_map_paths: dict[str, Path] = {}
    for label in sorted(unique_labels):
        out_path = district_dir / f"district_{label}.webp"
        if draw_district_image(out_path, label, district_geoms, state_geom):
            district_map_paths[label] = out_path
            rendered_base += 1

    rendered_sponsor = 0
    for rec in records:
        dist_label_raw = str(rec.get("district") or "").strip()
        dist_label = parse_district_label(dist_label_raw)
        base_path = district_map_paths.get(dist_label)
        if not base_path:
            continue
        slug = str(rec.get("slug") or f"district_{dist_label}".replace(" ", "_"))
        out_name = f"{slug}_district_map_standardized.webp"
        out_path = output_dir / out_name
        out_path.write_bytes(base_path.read_bytes())
        rec["standardized_district_map_image"] = {
            "mime_type": "image/webp",
            "local_path": str(out_path.as_posix()),
            "path": "/" + out_path.as_posix(),
            "source": str(base_path.as_posix()),
            "district_label": dist_label_raw,
        }
        rendered_sponsor += 1

    if args.write_json:
        Path(args.input_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Updated JSON: {args.input_json}")

    print(f"Rendered district base maps: {rendered_base} in {district_dir}")
    print(f"Rendered sponsor maps: {rendered_sponsor} in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
