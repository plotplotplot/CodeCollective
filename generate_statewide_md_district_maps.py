#!/usr/bin/env python3
"""Generate full-state Maryland district context maps from official PDFs.

Source: Maryland Planning redistricting PDF maps for districts 01..47.
Each sponsor gets a standardized map image with consistent Maryland outline.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

PDF_URL_TEMPLATE = (
    "https://planning.maryland.gov/Redistricting/Documents/2020Maps/Leg/"
    "2022-Legislative-District{district:02d}.pdf"
)


def fetch_pdf(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 0:
        return
    resp = requests.get(url, timeout=40)
    resp.raise_for_status()
    out_path.write_bytes(resp.content)


def pdf_to_png(pdf_path: Path, png_path: Path) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    if png_path.exists() and png_path.stat().st_size > 0:
        return
    cmd = [
        "pdftoppm",
        "-r",
        "90",
        "-f",
        "1",
        "-singlefile",
        "-png",
        str(pdf_path),
        str(png_path.with_suffix("")),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"pdftoppm failed for {pdf_path}: {proc.stderr.strip()}")


def crop_nonwhite(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB")
    px = rgb.load()
    w, h = rgb.size
    min_x, min_y = w, h
    max_x, max_y = 0, 0
    found = False
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r < 245 or g < 245 or b < 245:
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if not found:
        return rgb
    pad = 10
    left = max(0, min_x - pad)
    top = max(0, min_y - pad)
    right = min(w, max_x + pad + 1)
    bottom = min(h, max_y + pad + 1)
    return rgb.crop((left, top, right, bottom))


def fit_on_canvas(im: Image.Image, size: int = 800, margin: int = 24) -> Image.Image:
    canvas = Image.new("RGB", (size, size), (250, 250, 250))
    target = size - (2 * margin)
    src = im.copy()
    src.thumbnail((target, target), Image.Resampling.LANCZOS)
    x = (size - src.width) // 2
    y = (size - src.height) // 2
    canvas.paste(src, (x, y))
    return canvas


def annotate_label(im: Image.Image, label: str) -> Image.Image:
    out = im.copy()
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    text = f"District {label}"
    tx, ty = 20, 16
    # simple outlined text for readability
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        draw.text((tx + dx, ty + dy), text, fill=(255, 255, 255), font=font)
    draw.text((tx, ty), text, fill=(30, 30, 30), font=font)
    return out


def district_number(value: str) -> int | None:
    m = re.match(r"\s*(\d+)", str(value or ""))
    if not m:
        return None
    return int(m.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate statewide Maryland district context maps.")
    parser.add_argument("--input-json", default="data/mga_sponsors_2026.json")
    parser.add_argument("--pdf-cache", default="data/md_district_pdfs")
    parser.add_argument("--district-image-dir", default="images/md_district_statewide")
    parser.add_argument("--output-dir", default="images/politicians_standardized")
    parser.add_argument("--write-json", action="store_true")
    args = parser.parse_args()

    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = payload.get("records", [])
    if not records:
        raise SystemExit("No sponsor records found.")

    pdf_cache = Path(args.pdf_cache)
    district_dir = Path(args.district_image_dir)
    output_dir = Path(args.output_dir)
    district_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build one normalized full-state map image per district number.
    district_map_paths: dict[int, Path] = {}
    for n in range(1, 48):
        print(f"[{n:02d}/47] district map", flush=True)
        pdf_path = pdf_cache / f"district_{n:02d}.pdf"
        png_raw = district_dir / f"district_{n:02d}_raw.png"
        png_norm = district_dir / f"district_{n:02d}.png"
        fetch_pdf(PDF_URL_TEMPLATE.format(district=n), pdf_path)
        pdf_to_png(pdf_path, png_raw)
        normalized = fit_on_canvas(crop_nonwhite(Image.open(png_raw)))
        normalized.save(png_norm, format="PNG", optimize=True)
        district_map_paths[n] = png_norm

    rendered = 0
    for rec in records:
        dist_label = str(rec.get("district") or "").strip()
        n = district_number(dist_label)
        if n is None or n not in district_map_paths:
            continue
        base_im = Image.open(district_map_paths[n]).convert("RGB")
        sponsor_im = annotate_label(base_im, dist_label)
        slug = str(rec.get("slug") or f"district_{dist_label}".replace(" ", "_"))
        out_name = f"{slug}_district_map_standardized.png"
        out_path = output_dir / out_name
        sponsor_im.save(out_path, format="PNG", optimize=True)
        rec["standardized_district_map_image"] = {
            "mime_type": "image/png",
            "local_path": str(out_path.as_posix()),
            "path": "/" + out_path.as_posix(),
            "source": str(district_map_paths[n].as_posix()),
            "district_label": dist_label,
        }
        rendered += 1

    if args.write_json:
        Path(args.input_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Updated JSON: {args.input_json}")

    print(f"Rendered sponsor maps: {rendered}")
    print(f"District base maps: {len(district_map_paths)} in {district_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
