#!/usr/bin/env python3
"""Generate standardized full-Maryland district maps from MGA district images.

This version uses a fixed single-image template + inpainting workflow:
1) Select one reference district map as the statewide base.
2) Remove its highlighted district via neighborhood inpainting.
3) Detect each sponsor's highlighted district from their source map.
4) Draw the highlight onto the shared base.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import deque
from typing import Any

import numpy as np
from PIL import Image


def load_rgb(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"), dtype=np.uint8)


def detect_highlight_mask(arr: np.ndarray) -> np.ndarray:
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)

    # MGA district highlight is typically red/orange; keep thresholds broad.
    red_like = (r > 145) & (r - g > 18) & (r - b > 12)
    orange_like = (r > 155) & (g > 70) & (b < 150) & (r > g)
    mask = red_like | orange_like

    # Remove isolated noise pixels by requiring neighborhood support.
    neighbors = np.zeros(mask.shape, dtype=np.int16)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            neighbors += np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return mask & (neighbors >= 2)


def largest_component(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    best: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            q = deque([(y, x)])
            seen[y, x] = True
            comp: list[tuple[int, int]] = []
            while q:
                cy, cx = q.popleft()
                comp.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if len(comp) > len(best):
                best = comp
    out = np.zeros_like(mask)
    for y, x in best:
        out[y, x] = True
    return out


def dilate(mask: np.ndarray, steps: int = 1) -> np.ndarray:
    out = mask.copy()
    for _ in range(steps):
        grown = out.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                grown |= np.roll(np.roll(out, dy, axis=0), dx, axis=1)
        out = grown
    return out


def inner_mask(mask: np.ndarray) -> np.ndarray:
    out = mask.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            out &= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return out & mask


def inpaint_highlight_region(base: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Inpaint highlighted area using iterative neighborhood averaging."""
    out = base.astype(np.float32).copy()
    work = mask.copy()
    h, w = work.shape
    for _ in range(120):
        if not work.any():
            break
        border = np.zeros_like(work)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                border |= work & ~np.roll(np.roll(work, dy, axis=0), dx, axis=1)
        ys, xs = np.where(border)
        if not len(xs):
            break
        for y, x in zip(ys.tolist(), xs.tolist()):
            vals = []
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and not work[ny, nx]:
                        vals.append(out[ny, nx])
            if vals:
                out[y, x] = np.mean(np.array(vals), axis=0)
        work[border] = False
    if work.any():
        mean_bg = out[~mask].mean(axis=0) if (~mask).any() else np.array([236, 236, 236], dtype=np.float32)
        out[work] = mean_bg
    return out.astype(np.uint8)


def render_standardized_map(base: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = base.copy()
    inner = inner_mask(mask)
    edge = mask & ~inner
    out[mask] = np.array([255, 214, 101], dtype=np.uint8)
    out[edge] = np.array([224, 133, 21], dtype=np.uint8)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Standardize MGA district map images.")
    parser.add_argument(
        "--input-json",
        default="data/mga_sponsors_2026.json",
        help="Sponsor JSON with district_map_image paths.",
    )
    parser.add_argument(
        "--output-dir",
        default="images/politicians_standardized",
        help="Directory for standardized maps.",
    )
    parser.add_argument(
        "--write-json",
        action="store_true",
        help="Write standardized_district_map_image metadata back into input JSON.",
    )
    args = parser.parse_args()

    json_path = Path(args.input_json)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = payload.get("records", [])
    if not records:
        raise SystemExit("No records found in sponsor JSON.")

    image_paths: list[Path] = []
    valid_records: list[dict[str, Any]] = []
    for rec in records:
        img = rec.get("district_map_image") or {}
        local = img.get("local_path")
        if not local:
            continue
        p = Path(local)
        if not p.exists():
            continue
        image_paths.append(p)
        valid_records.append(rec)

    if not image_paths:
        raise SystemExit("No existing district map images found.")

    images = [load_rgb(p) for p in image_paths]
    shapes = {img.shape for img in images}
    if len(shapes) != 1:
        raise SystemExit(f"District maps must share a common size; got: {shapes}")

    # Use first map as reference for base geometry, then inpaint out its highlight.
    ref = images[0]
    ref_mask = largest_component(detect_highlight_mask(ref))
    ref_mask = dilate(ref_mask, steps=1)
    base = inpaint_highlight_region(ref, ref_mask)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for rec, src in zip(valid_records, images):
        mask = largest_component(detect_highlight_mask(src))
        if mask.any():
            mask = dilate(mask, steps=1)
        slug = str(rec.get("slug") or "member")
        out_name = f"{slug}_district_map_standardized.png"
        out_path = out_dir / out_name
        rendered = render_standardized_map(base, mask)
        Image.fromarray(rendered, mode="RGB").save(out_path, format="PNG", optimize=True)

        if args.write_json:
            rec["standardized_district_map_image"] = {
                "mime_type": "image/png",
                "local_path": str(out_path.as_posix()),
                "path": "/" + out_path.as_posix(),
            }

    if args.write_json:
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Updated JSON with standardized map paths: {json_path}")

    print(f"Wrote standardized maps to: {out_dir}")
    print(f"Rendered maps: {len(valid_records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
