#!/usr/bin/env python3
"""
Build a single-folder 1000-image review set at preview size.

Composition:
- base1000_no_rare manifest (default source for each token)
- rare98 selection folder (token-specific replacement)
- superrare2 images (token-specific replacement)

Default superrare mapping:
- token 999 -> corelogo (art/tmp/Core1.png)
- token 1000 -> pinglogo (art/tmp/Ping1.png)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE = ROOT / "manifests" / "base1000_no_rare_latest.json"
DEFAULT_RARE_DIR = ROOT / "art" / "candidates" / "rare_wave1" / "選定"
DEFAULT_OUT_DIR = ROOT / "art" / "review" / "final1000_preview_v1" / "png"
DEFAULT_OUT_MANIFEST = ROOT / "manifests" / "final1000_review_manifest_v1.json"

DEFAULT_SUPER_1_TOKEN = 999
DEFAULT_SUPER_2_TOKEN = 1000
DEFAULT_SUPER_1_FILE = ROOT / "art" / "tmp" / "Core1.png"
DEFAULT_SUPER_2_FILE = ROOT / "art" / "tmp" / "Ping1.png"

RARE_NAME_RE = re.compile(
    r"^(?P<token>\d+)__.*__rare_(?P<rtype>odd_eyes|red_nose|blue_nose|glasses|sunglasses)\.png$",
    re.IGNORECASE,
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as rf:
        for chunk in iter(lambda: rf.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def fit_to_size(img: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    if img.size == target_size:
        return img
    tw, th = target_size
    sw, sh = img.size
    # nearest-neighbor integer scale only (pixel-art safe)
    if tw % sw == 0 and th % sh == 0 and (tw // sw) == (th // sh):
        return img.resize(target_size, Image.NEAREST)
    raise RuntimeError(f"Cannot fit image size {img.size} -> {target_size}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build final 1000 review image set.")
    p.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE)
    p.add_argument("--rare-dir", type=Path, default=DEFAULT_RARE_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--out-manifest", type=Path, default=DEFAULT_OUT_MANIFEST)
    p.add_argument("--super1-token", type=int, default=DEFAULT_SUPER_1_TOKEN)
    p.add_argument("--super2-token", type=int, default=DEFAULT_SUPER_2_TOKEN)
    p.add_argument("--super1-file", type=Path, default=DEFAULT_SUPER_1_FILE)
    p.add_argument("--super2-file", type=Path, default=DEFAULT_SUPER_2_FILE)
    return p.parse_args()


def load_base_map(base_manifest: Path) -> dict[int, dict]:
    obj = json.loads(base_manifest.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    if len(items) != 1000:
        raise RuntimeError(f"Expected 1000 base items, got {len(items)}")
    m = {}
    for it in items:
        tid = int(it["token_id"])
        if tid in m:
            raise RuntimeError(f"Duplicate token_id in base manifest: {tid}")
        m[tid] = it
    return m


def load_rare_map(rare_dir: Path) -> dict[int, dict]:
    if not rare_dir.exists():
        raise FileNotFoundError(f"Rare dir not found: {rare_dir}")
    m: dict[int, dict] = {}
    for p in sorted(rare_dir.glob("*.png")):
        mm = RARE_NAME_RE.match(p.name)
        if not mm:
            continue
        tid = int(mm.group("token"))
        if tid in m:
            raise RuntimeError(f"Duplicate token_id in rare set: {tid}")
        m[tid] = {"path": p, "rarity_type": mm.group("rtype").lower()}
    if len(m) != 98:
        raise RuntimeError(f"Expected 98 rare files, got {len(m)}")
    return m


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
    if not args.super1_file.exists() or not args.super2_file.exists():
        raise FileNotFoundError("Missing superrare source file(s)")
    if args.super1_token == args.super2_token:
        raise ValueError("super1-token and super2-token must be different")

    base_map = load_base_map(args.base_manifest)
    rare_map = load_rare_map(args.rare_dir)

    super_map = {
        args.super1_token: ("corelogo", args.super1_file),
        args.super2_token: ("pinglogo", args.super2_file),
    }
    for tid in super_map:
        if tid < 1 or tid > 1000:
            raise ValueError(f"Superrare token out of range: {tid}")
        if tid in rare_map:
            raise RuntimeError(f"Superrare token overlaps rare98 token: {tid}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    clean_pngs(args.out_dir)

    counts = Counter()
    review_items = []

    for tid in range(1, 1001):
        base_item = base_map[tid]
        base_path = ROOT / base_item["file"]
        if not base_path.exists():
            raise FileNotFoundError(f"Base image file missing: {base_path}")

        source_tier = "base"
        rarity_type = None
        src_desc = base_item["file"]
        out_img_path = args.out_dir / f"{tid:04d}__base.png"

        if tid in super_map:
            source_tier = "superrare"
            rarity_type, src_super = super_map[tid]
            base_img = load_rgba(base_path)
            super_img = fit_to_size(load_rgba(src_super), base_img.size)
            super_img.save(out_img_path := args.out_dir / f"{tid:04d}__superrare_{rarity_type}.png", format="PNG", optimize=False)
            src_desc = rel(src_super)
        elif tid in rare_map:
            source_tier = "rare"
            rarity_type = rare_map[tid]["rarity_type"]
            src = rare_map[tid]["path"]
            out_img_path = args.out_dir / f"{tid:04d}__rare_{rarity_type}.png"
            shutil.copy2(src, out_img_path)
            src_desc = rel(src)
        else:
            shutil.copy2(base_path, out_img_path)

        counts[source_tier] += 1
        review_items.append(
            {
                "token_id": tid,
                "review_file": rel(out_img_path),
                "source_tier": source_tier,
                "rarity_type": rarity_type,
                "source_file": src_desc,
                "base_file": base_item["file"],
                "collar": bool(base_item.get("collar", False)),
                "collar_id": base_item.get("collar_id"),
            }
        )

    if len(review_items) != 1000:
        raise RuntimeError(f"Review items != 1000: {len(review_items)}")
    if counts["rare"] != 98 or counts["superrare"] != 2:
        raise RuntimeError(f"Unexpected rare/super counts: {dict(counts)}")

    collar_counter = Counter()
    for it in review_items:
        if it["source_tier"] in {"rare", "superrare"}:
            collar_counter["with_collar" if it["collar"] else "without_collar"] += 1

    out_obj = {
        "version": "final1000_review_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "base_manifest": rel(args.base_manifest),
            "base_manifest_sha256": file_sha256(args.base_manifest),
            "rare_dir": rel(args.rare_dir),
            "super1": {"token_id": args.super1_token, "file": rel(args.super1_file), "rarity_type": "corelogo"},
            "super2": {"token_id": args.super2_token, "file": rel(args.super2_file), "rarity_type": "pinglogo"},
        },
        "counts": {
            "total": 1000,
            "base": counts["base"],
            "rare": counts["rare"],
            "superrare": counts["superrare"],
            "modified_total": counts["rare"] + counts["superrare"],
            "modified_with_collar": collar_counter["with_collar"],
            "modified_without_collar": collar_counter["without_collar"],
        },
        "items": review_items,
    }
    args.out_manifest.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[final-review] out_dir={args.out_dir}")
    print(f"[final-review] out_manifest={args.out_manifest}")
    print(f"[final-review] counts base={counts['base']} rare={counts['rare']} superrare={counts['superrare']}")
    print(f"[final-review] modified collar with={collar_counter['with_collar']} without={collar_counter['without_collar']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
