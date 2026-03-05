#!/usr/bin/env python3
"""
Create a clean README preview grid image from review set PNGs.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "art" / "review" / "final1000_preview_v1" / "png"
DEFAULT_OUTPUT = ROOT / "docs" / "assets" / "core_cats_preview_grid.png"


TOKEN_RE = re.compile(r"^(\d{4})__")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate README preview grid image.")
    p.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--cols", type=int, default=12)
    p.add_argument("--rows", type=int, default=8)
    p.add_argument("--tile", type=int, default=72)
    p.add_argument("--gap", type=int, default=6)
    p.add_argument("--padding", type=int, default=14)
    return p.parse_args()


def sort_key(path: Path) -> tuple[int, str]:
    m = TOKEN_RE.match(path.name)
    if m:
        return (int(m.group(1)), path.name)
    return (10**9, path.name)


def evenly_spaced(seq: list[Path], k: int) -> list[Path]:
    if k >= len(seq):
        return seq[:]
    if k <= 1:
        return [seq[0]]
    out = []
    for i in range(k):
        idx = round(i * (len(seq) - 1) / (k - 1))
        out.append(seq[idx])
    return out


def main() -> int:
    args = parse_args()
    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")

    pngs = sorted([p for p in args.input_dir.glob("*.png") if p.is_file()], key=sort_key)
    if not pngs:
        raise RuntimeError(f"No PNG files found in: {args.input_dir}")

    slots = args.cols * args.rows
    chosen = evenly_spaced(pngs, slots)

    w = args.padding * 2 + args.cols * args.tile + (args.cols - 1) * args.gap
    h = args.padding * 2 + args.rows * args.tile + (args.rows - 1) * args.gap
    canvas = Image.new("RGBA", (w, h), (39, 49, 60, 255))

    for i, src in enumerate(chosen):
        r = i // args.cols
        c = i % args.cols
        x = args.padding + c * (args.tile + args.gap)
        y = args.padding + r * (args.tile + args.gap)

        img = Image.open(src).convert("RGBA")
        tile = ImageOps.contain(img, (args.tile, args.tile), method=Image.NEAREST)
        # Center in tile
        box = Image.new("RGBA", (args.tile, args.tile), (28, 35, 44, 255))
        bx = (args.tile - tile.width) // 2
        by = (args.tile - tile.height) // 2
        box.alpha_composite(tile, (bx, by))
        canvas.alpha_composite(box, (x, y))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, format="PNG", optimize=True)
    print(f"[preview-grid] input={args.input_dir}")
    print(f"[preview-grid] output={args.output}")
    print(f"[preview-grid] selected={len(chosen)} from total={len(pngs)}")
    print(f"[preview-grid] grid={args.cols}x{args.rows} tile={args.tile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
