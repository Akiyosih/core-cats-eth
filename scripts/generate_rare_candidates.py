#!/usr/bin/env python3
"""
Generate rare candidates from base1000 manifest (one rare trait per token).

Outputs:
- art/parts/rare/*.png                 (normalized English-ID rare assets)
- art/candidates/rare_wave1/png/*.png  (candidate images)
- manifests/rare_wave1_candidates.jsonl
- manifests/rare_wave1_candidates_summary.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE_MANIFEST = ROOT / "manifests" / "base1000_no_rare_latest.json"
DEFAULT_OUT_DIR = ROOT / "art" / "candidates" / "rare_wave1" / "png"
DEFAULT_MANIFEST = ROOT / "manifests" / "rare_wave1_candidates.jsonl"
DEFAULT_SUMMARY = ROOT / "manifests" / "rare_wave1_candidates_summary.json"
DEFAULT_RARE_PARTS_DIR = ROOT / "art" / "parts" / "rare"

# Existing source assets (Japanese names in repo).
ODD_EYES_SRC = ROOT / "art" / "parts" / "eyes" / "\u30aa\u30c3\u30c8\u3099\u30a2\u30a4.png"
SUNGLASSES_SRC = ROOT / "art" / "parts" / "masks" / "\u30b5\u30f3\u30af\u3099\u30e9\u30b9.png"
GLASSES_SRC = ROOT / "art" / "parts" / "masks" / "\u30e1\u30ab\u3099\u30cd.png"
NOSE_SRC = ROOT / "art" / "parts" / "noses" / "\u9f3b.png"

RARE_TYPES = ("odd_eyes", "red_nose", "blue_nose", "glasses", "sunglasses")
WEIGHTS_98 = {
    "odd_eyes": 39,
    "red_nose": 20,
    "blue_nose": 20,
    "glasses": 10,
    "sunglasses": 9,
}

# Nose tint presets.
RED_NOSE_RGB = (230, 70, 70)
BLUE_NOSE_RGB = (70, 130, 255)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as rf:
        for chunk in iter(lambda: rf.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_counts(raw: str | None, total: int) -> dict[str, int]:
    if raw:
        parsed: dict[str, int] = {}
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            if "=" not in token:
                raise ValueError(f"Invalid --counts token: {token}")
            k, v = token.split("=", 1)
            k = k.strip()
            if k not in RARE_TYPES:
                raise ValueError(f"Unknown rare type in --counts: {k}")
            parsed[k] = int(v.strip())
        for rt in RARE_TYPES:
            parsed.setdefault(rt, 0)
        if sum(parsed.values()) != total:
            raise ValueError(f"--counts total must be {total}, got {sum(parsed.values())}")
        return parsed

    # Default: scale 98-target weights to requested total with largest remainder.
    weight_sum = sum(WEIGHTS_98.values())  # 98
    base = {}
    frac = []
    assigned = 0
    for rt in RARE_TYPES:
        raw_v = total * WEIGHTS_98[rt] / weight_sum
        i = int(raw_v)
        base[rt] = i
        assigned += i
        frac.append((raw_v - i, rt))
    remain = total - assigned
    frac.sort(key=lambda x: (-x[0], x[1]))
    for i in range(remain):
        base[frac[i][1]] += 1
    return base


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate 1-rare-per-token candidates.")
    p.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    p.add_argument("--count", type=int, default=200)
    p.add_argument("--seed", type=int, default=20260305)
    p.add_argument(
        "--counts",
        type=str,
        default=None,
        help="Optional explicit counts: odd_eyes=80,red_nose=41,blue_nose=41,glasses=20,sunglasses=18",
    )
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    p.add_argument("--rare-parts-dir", type=Path, default=DEFAULT_RARE_PARTS_DIR)
    return p.parse_args()


def load_rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def fit_overlay_to_base(base_img: Image.Image, overlay_img: Image.Image) -> Image.Image:
    if base_img.size == overlay_img.size:
        return overlay_img
    bw, bh = base_img.size
    ow, oh = overlay_img.size
    if bw % ow == 0 and bh % oh == 0 and (bw // ow) == (bh // oh):
        return overlay_img.resize((bw, bh), Image.NEAREST)
    raise RuntimeError(f"Size mismatch: base={base_img.size}, overlay={overlay_img.size}")


def colorize_mask(mask_img: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    out = mask_img.copy().convert("RGBA")
    pix = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            _, _, _, a = pix[x, y]
            if a > 0:
                pix[x, y] = (rgb[0], rgb[1], rgb[2], a)
    return out


def build_rare_parts(rare_parts_dir: Path) -> dict[str, Path]:
    for src in (ODD_EYES_SRC, SUNGLASSES_SRC, GLASSES_SRC, NOSE_SRC):
        if not src.exists():
            raise FileNotFoundError(f"Missing source rare part: {src}")

    rare_parts_dir.mkdir(parents=True, exist_ok=True)

    out_map = {
        "odd_eyes": rare_parts_dir / "odd_eyes.png",
        "sunglasses": rare_parts_dir / "sunglasses.png",
        "glasses": rare_parts_dir / "glasses.png",
        "red_nose": rare_parts_dir / "red_nose.png",
        "blue_nose": rare_parts_dir / "blue_nose.png",
    }

    shutil.copy2(ODD_EYES_SRC, out_map["odd_eyes"])
    shutil.copy2(SUNGLASSES_SRC, out_map["sunglasses"])
    shutil.copy2(GLASSES_SRC, out_map["glasses"])

    nose_mask = load_rgba(NOSE_SRC)
    colorize_mask(nose_mask, RED_NOSE_RGB).save(out_map["red_nose"], format="PNG", optimize=False)
    colorize_mask(nose_mask, BLUE_NOSE_RGB).save(out_map["blue_nose"], format="PNG", optimize=False)
    return out_map


def clean_pngs(target_dir: Path) -> None:
    if not target_dir.exists():
        return
    for p in target_dir.glob("*.png"):
        if p.is_file():
            p.unlink()


def main() -> int:
    args = parse_args()
    if not args.base_manifest.exists():
        raise FileNotFoundError(f"Missing base manifest: {args.base_manifest}")
    if args.count <= 0:
        raise ValueError("--count must be > 0")

    base = json.loads(args.base_manifest.read_text(encoding="utf-8"))
    items = base.get("items", [])
    if len(items) != 1000:
        raise RuntimeError(f"Expected 1000 base items, got {len(items)}")

    token_map = {}
    for it in items:
        tid = it.get("token_id")
        if tid in token_map:
            raise RuntimeError(f"Duplicate token_id in base manifest: {tid}")
        token_map[tid] = it
    token_ids = sorted(token_map.keys())
    if len(token_ids) < args.count:
        raise RuntimeError(f"Not enough tokens: have {len(token_ids)}, need {args.count}")

    rare_counts = parse_counts(args.counts, args.count)
    type_list = []
    for rt in RARE_TYPES:
        type_list.extend([rt] * rare_counts[rt])
    if len(type_list) != args.count:
        raise RuntimeError("Internal count mismatch")

    rng = random.Random(args.seed)
    selected_token_ids = rng.sample(token_ids, args.count)
    rng.shuffle(type_list)

    rare_parts = build_rare_parts(args.rare_parts_dir)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    clean_pngs(args.out_dir)

    records = []
    by_type = Counter()
    for idx, (tid, rt) in enumerate(zip(selected_token_ids, type_list)):
        base_item = token_map[tid]
        base_file = ROOT / base_item["file"]
        if not base_file.exists():
            raise FileNotFoundError(f"Base image file not found: {base_file}")

        base_img = load_rgba(base_file)
        overlay_img = load_rgba(rare_parts[rt])
        overlay_img = fit_overlay_to_base(base_img, overlay_img)

        merged = base_img.copy()
        merged.alpha_composite(overlay_img)

        out_name = f"{tid:04d}__{Path(base_item['file']).stem}__rare_{rt}.png"
        out_path = args.out_dir / out_name
        merged.save(out_path, format="PNG", optimize=False)

        by_type[rt] += 1
        records.append(
            {
                "file": rel(out_path),
                "token_id": tid,
                "base_file": base_item["file"],
                "origin_file_24": base_item.get("origin_file_24"),
                "source_kind": base_item.get("source_kind"),
                "collar": bool(base_item.get("collar")),
                "collar_id": base_item.get("collar_id"),
                "rarity_tier": "rare",
                "rarity_type": rt,
                "part_file_24": rel(rare_parts[rt]),
                "seed": args.seed,
                "index": idx,
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    with args.manifest.open("w", encoding="utf-8") as wf:
        for rec in records:
            wf.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summary = {
        "version": "rare_wave1_candidates_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_base_manifest": rel(args.base_manifest),
        "input_base_manifest_sha256": file_sha256(args.base_manifest),
        "seed": args.seed,
        "count": args.count,
        "counts_by_type": {rt: by_type.get(rt, 0) for rt in RARE_TYPES},
        "rare_parts": {rt: rel(path) for rt, path in rare_parts.items()},
        "output_dir": rel(args.out_dir),
        "manifest_jsonl": rel(args.manifest),
        "token_ids": sorted(selected_token_ids),
    }
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[rare-candidates] generated={len(records)} out_dir={args.out_dir}")
    for rt in RARE_TYPES:
        print(f"[rare-candidates] {rt}: {by_type.get(rt, 0)}")
    print(f"[rare-candidates] manifest={args.manifest}")
    print(f"[rare-candidates] summary={args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
