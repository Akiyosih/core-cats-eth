#!/usr/bin/env python3
"""
Generate collar-on variants from the already selected base set.

- Input:  art/selected/png/*.png (e.g. 600 base images)
- Input:  art/parts/accessories/collar/*.png (2 collar overlays)
- Output: art/candidates/collar_wave1/png/*.png
- Output: manifests/collar_wave1_candidates.jsonl

The script never mutates the base set. It only writes to candidate paths.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_DIR = ROOT / "art" / "selected" / "png"
DEFAULT_COLLAR_DIR = ROOT / "art" / "parts" / "accessories" / "collar"
DEFAULT_OUT_DIR = ROOT / "art" / "candidates" / "collar_wave1" / "png"
DEFAULT_MANIFEST = ROOT / "manifests" / "collar_wave1_candidates.jsonl"


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create collar candidates from selected base PNGs."
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=DEFAULT_BASE_DIR,
        help=f"Base selected PNG dir (default: {DEFAULT_BASE_DIR})",
    )
    parser.add_argument(
        "--collar-dir",
        type=Path,
        default=DEFAULT_COLLAR_DIR,
        help=f"Collar overlay PNG dir (default: {DEFAULT_COLLAR_DIR})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output candidate PNG dir (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Output JSONL manifest (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260305,
        help="Random seed for reproducible collar assignment (default: 20260305)",
    )
    return parser.parse_args()


def load_pngs(target_dir: Path) -> list[Path]:
    if not target_dir.exists():
        raise FileNotFoundError(f"Directory not found: {target_dir}")
    files = sorted([p for p in target_dir.glob("*.png") if p.is_file()])
    if not files:
        raise RuntimeError(f"No PNG files found in: {target_dir}")
    return files


def load_rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def fit_overlay_to_base(
    base_img: Image.Image, overlay_img: Image.Image, base_path: Path, overlay_path: Path
) -> Image.Image:
    """
    Allow composing 24x24 overlays onto upscaled previews (e.g. 768x768).
    """
    if base_img.size == overlay_img.size:
        return overlay_img

    bw, bh = base_img.size
    ow, oh = overlay_img.size

    # Scale only when both axes are the same integer factor (nearest-neighbor).
    if bw % ow == 0 and bh % oh == 0 and (bw // ow) == (bh // oh):
        return overlay_img.resize((bw, bh), Image.NEAREST)

    raise RuntimeError(
        f"Size mismatch: base={base_path.name}({base_img.size}) "
        f"collar={overlay_path.name}({overlay_img.size})"
    )


def build_record(
    out_file: Path,
    base_file: Path,
    collar_file: Path,
    seed: int,
    index: int,
) -> Dict[str, object]:
    return {
        "file": rel_path(out_file),
        "base_file": rel_path(base_file),
        "base_filename": base_file.name,
        "collar_id": collar_file.stem,
        "collar_file": rel_path(collar_file),
        "seed": seed,
        "index": index,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> int:
    args = parse_args()

    base_files = load_pngs(args.base_dir)
    collar_files = load_pngs(args.collar_dir)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    counts = Counter()

    records: list[dict] = []
    for idx, base_path in enumerate(base_files):
        collar_path = rng.choice(collar_files)
        counts[collar_path.stem] += 1

        base_img = load_rgba(base_path)
        collar_img = load_rgba(collar_path)
        collar_img = fit_overlay_to_base(base_img, collar_img, base_path, collar_path)

        merged = base_img.copy()
        merged.alpha_composite(collar_img)

        out_name = f"{base_path.stem}__collar_{collar_path.stem}.png"
        out_path = args.out_dir / out_name
        merged.save(out_path, format="PNG", optimize=False)

        records.append(build_record(out_path, base_path, collar_path, args.seed, idx))

    with args.manifest.open("w", encoding="utf-8") as wf:
        for rec in records:
            wf.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[collar-candidates] base={len(base_files)} generated={len(records)}")
    print(f"[collar-candidates] out_dir={args.out_dir}")
    print(f"[collar-candidates] manifest={args.manifest}")
    for collar_id, n in sorted(counts.items()):
        print(f"[collar-candidates] {collar_id}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
