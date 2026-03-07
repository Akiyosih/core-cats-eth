#!/usr/bin/env python3
"""
Build canonical final-1000 manifest and 24x24 PNG set.

Input:
- manifests/base1000_no_rare_latest.json
- manifests/final1000_review_manifest_v1.json

Output:
- art/final/final1000_v1/png24/0001.png ... 1000.png
- manifests/final_1000_manifest_v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE_MANIFEST = ROOT / "manifests" / "base1000_no_rare_latest.json"
DEFAULT_REVIEW_MANIFEST = ROOT / "manifests" / "final1000_review_manifest_v1.json"
DEFAULT_OUT_DIR = ROOT / "art" / "final" / "final1000_v1" / "png24"
DEFAULT_OUT_MANIFEST = ROOT / "manifests" / "final_1000_manifest_v1.json"
DEFAULT_BASE_LAYER_24 = ROOT / "art" / "base" / "base.png"

RARE_OVERLAY_BY_TYPE = {
    "odd_eyes": ROOT / "art" / "parts" / "rare" / "odd_eyes.png",
    "red_nose": ROOT / "art" / "parts" / "rare" / "red_nose.png",
    "blue_nose": ROOT / "art" / "parts" / "rare" / "blue_nose.png",
    "glasses": ROOT / "art" / "parts" / "rare" / "glasses.png",
    "sunglasses": ROOT / "art" / "parts" / "rare" / "sunglasses.png",
}

RARE_TYPES = set(RARE_OVERLAY_BY_TYPE.keys())
SUPERRARE_TYPE_MAP = {
    "corelogo_1": "corelogo",
    "corelogo_2": "pinglogo",
    "corelogo": "corelogo",
    "pinglogo": "pinglogo",
}
SUPERRARE_TYPES = {"corelogo", "pinglogo"}
SOURCE_TIERS = {"base", "rare", "superrare"}
OUTPUT_RARITY_TIER_MAP = {
    "base": "common",
    "rare": "rare",
    "superrare": "superrare",
}
TARGET_SIZE = (24, 24)


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


def fit_to_size(img: Image.Image, target_size: tuple[int, int], label: str) -> Image.Image:
    if img.size == target_size:
        return img
    tw, th = target_size
    sw, sh = img.size
    if tw % sw == 0 and th % sh == 0 and (tw // sw) == (th // sh):
        return img.resize(target_size, Image.NEAREST)
    raise RuntimeError(f"Cannot fit {label} size {img.size} -> {target_size}")


def clean_pngs(target_dir: Path) -> None:
    if not target_dir.exists():
        return
    for p in target_dir.glob("*.png"):
        if p.is_file():
            p.unlink()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build canonical final1000 manifest and 24x24 PNGs.")
    p.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    p.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_MANIFEST)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--out-manifest", type=Path, default=DEFAULT_OUT_MANIFEST)
    p.add_argument("--base-layer-24", type=Path, default=DEFAULT_BASE_LAYER_24)
    p.add_argument(
        "--superrare-collar-mode",
        choices=("inherit", "false", "true"),
        default="false",
        help="How collar trait is set for superrare tokens.",
    )
    p.add_argument(
        "--superrare-pattern",
        type=str,
        default="superrare",
        help="Pattern trait value for superrare tokens.",
    )
    p.add_argument(
        "--superrare-palette",
        type=str,
        default="superrare",
        help="Color Variation (palette_id) for superrare tokens.",
    )
    p.add_argument(
        "--keep-existing-pngs",
        action="store_true",
        help="Do not clean existing PNGs in --out-dir before writing.",
    )
    return p.parse_args()


def load_base_map(path: Path) -> dict[int, dict]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    if len(items) != 1000:
        raise RuntimeError(f"Expected 1000 base items, got {len(items)}")
    out: dict[int, dict] = {}
    for it in items:
        tid = int(it["token_id"])
        if tid in out:
            raise RuntimeError(f"Duplicate token_id in base manifest: {tid}")
        out[tid] = it
    return out


def load_review_map(path: Path) -> dict[int, dict]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    if len(items) != 1000:
        raise RuntimeError(f"Expected 1000 review items, got {len(items)}")
    out: dict[int, dict] = {}
    for it in items:
        tid = int(it["token_id"])
        if tid in out:
            raise RuntimeError(f"Duplicate token_id in review manifest: {tid}")
        out[tid] = it
    return out


def build_attributes(
    *,
    pattern: str,
    palette_id: str,
    collar: bool,
    collar_id: str | None,
    rarity_tier: str,
    rarity_type: str,
) -> list[dict[str, str]]:
    collar_value = str(collar_id) if collar and collar_id else "none"
    return [
        {"trait_type": "Pattern", "value": pattern},
        {"trait_type": "Color Variation", "value": palette_id},
        {"trait_type": "Collar", "value": collar_value},
        {"trait_type": "Rarity Tier", "value": rarity_tier},
        {"trait_type": "Rarity Type", "value": rarity_type},
    ]


def superrare_collar_fields(mode: str, base_item: dict) -> tuple[bool, str | None]:
    if mode == "inherit":
        return bool(base_item.get("collar")), base_item.get("collar_id")
    if mode == "false":
        return False, None
    return True, str(base_item.get("collar_id") or "forced")


def main() -> int:
    args = parse_args()

    if not args.base_manifest.exists():
        raise FileNotFoundError(f"Missing base manifest: {args.base_manifest}")
    if not args.review_manifest.exists():
        raise FileNotFoundError(f"Missing review manifest: {args.review_manifest}")
    if not args.base_layer_24.exists():
        raise FileNotFoundError(f"Missing base layer file: {args.base_layer_24}")

    for rt, overlay in RARE_OVERLAY_BY_TYPE.items():
        if not overlay.exists():
            raise FileNotFoundError(f"Missing rare overlay for {rt}: {overlay}")

    base_map = load_base_map(args.base_manifest)
    review_map = load_review_map(args.review_manifest)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    if not args.keep_existing_pngs:
        clean_pngs(args.out_dir)

    items_out: list[dict] = []
    by_tier = Counter()
    by_type = Counter()
    by_pattern = Counter()
    by_palette = Counter()
    by_collar_state = Counter()
    by_collar_type = Counter()
    base_layer_img = fit_to_size(load_rgba(args.base_layer_24), TARGET_SIZE, "base layer 24")

    for tid in range(1, 1001):
        base_item = base_map.get(tid)
        review_item = review_map.get(tid)
        if base_item is None or review_item is None:
            raise RuntimeError(f"Missing token_id={tid} in input manifests")

        source_tier = str(review_item["source_tier"])
        if source_tier not in SOURCE_TIERS:
            raise RuntimeError(f"Invalid source_tier for token {tid}: {source_tier}")
        rarity_tier = OUTPUT_RARITY_TIER_MAP.get(source_tier)
        if rarity_tier is None:
            raise RuntimeError(f"No output rarity_tier mapping for source_tier={source_tier}")

        rarity_type_raw = review_item.get("rarity_type")
        rarity_type_raw = str(rarity_type_raw) if rarity_type_raw else "none"
        rarity_type = rarity_type_raw

        base_origin_rel = str(base_item["origin_file_24"])
        base_origin_path = ROOT / base_origin_rel
        if not base_origin_path.exists():
            raise FileNotFoundError(f"Missing base origin file for token {tid}: {base_origin_path}")

        pattern_img = fit_to_size(load_rgba(base_origin_path), TARGET_SIZE, f"base token {tid}")
        composed_base_img = pattern_img.copy()
        # Canonical composition: pattern layer first, then base body/outline.
        composed_base_img.alpha_composite(base_layer_img)

        final_img: Image.Image
        layers_24: list[dict[str, str]]
        pattern: str
        palette_id: str
        category: str
        color_tuple: list[str] | None
        variant_key: str | None
        slots: int | None
        collar: bool
        collar_id: str | None
        source_file_rel = str(review_item.get("source_file") or base_item.get("file"))

        if source_tier == "superrare":
            rarity_type = SUPERRARE_TYPE_MAP.get(rarity_type_raw, "")
            if rarity_type not in SUPERRARE_TYPES:
                raise RuntimeError(f"Invalid superrare type for token {tid}: {rarity_type_raw}")

            super_path = ROOT / source_file_rel
            if not super_path.exists():
                raise FileNotFoundError(f"Missing superrare source file for token {tid}: {super_path}")

            final_img = fit_to_size(load_rgba(super_path), TARGET_SIZE, f"superrare token {tid}")
            layers_24 = [{"kind": "superrare_override", "file": rel(super_path)}]

            collar, collar_id = superrare_collar_fields(args.superrare_collar_mode, base_item)
            pattern = args.superrare_pattern
            palette_id = args.superrare_palette
            category = "superrare"
            color_tuple = None
            variant_key = None
            slots = None
        else:
            if source_tier == "rare" and rarity_type not in RARE_TYPES:
                raise RuntimeError(f"Invalid rare type for token {tid}: {rarity_type}")
            if source_tier == "base" and rarity_type != "none":
                raise RuntimeError(f"Base token must have rarity_type=none: token {tid}")

            final_img = composed_base_img.copy()
            layers_24 = [
                {"kind": "pattern", "file": rel(base_origin_path)},
                {"kind": "base_layer", "file": rel(args.base_layer_24)},
            ]

            collar = bool(base_item.get("collar"))
            collar_id = base_item.get("collar_id")
            if collar:
                collar_overlay_rel = base_item.get("collar_overlay_file_24")
                if not collar_overlay_rel:
                    raise RuntimeError(f"Missing collar overlay in base item token {tid}")
                collar_overlay_path = ROOT / str(collar_overlay_rel)
                if not collar_overlay_path.exists():
                    raise FileNotFoundError(f"Missing collar overlay file for token {tid}: {collar_overlay_path}")
                collar_overlay = fit_to_size(
                    load_rgba(collar_overlay_path),
                    TARGET_SIZE,
                    f"collar token {tid}",
                )
                final_img.alpha_composite(collar_overlay)
                layers_24.append({"kind": "collar", "file": rel(collar_overlay_path)})

            if source_tier == "rare":
                rare_overlay_path = RARE_OVERLAY_BY_TYPE[rarity_type]
                rare_overlay = fit_to_size(
                    load_rgba(rare_overlay_path),
                    TARGET_SIZE,
                    f"rare {rarity_type} token {tid}",
                )
                final_img.alpha_composite(rare_overlay)
                layers_24.append({"kind": "rare", "file": rel(rare_overlay_path)})

            pattern = str(base_item["pattern"])
            palette_id = str(base_item["palette_id"])
            category = str(base_item["category"])
            color_tuple = list(base_item.get("color_tuple") or [])
            variant_key = str(base_item["variant_key"])
            slots = int(base_item["slots"])

        out_png_path = args.out_dir / f"{tid:04d}.png"
        final_img.save(out_png_path, format="PNG", optimize=False)

        by_tier[rarity_tier] += 1
        by_type[rarity_type] += 1
        by_pattern[pattern] += 1
        by_palette[palette_id] += 1
        by_collar_state["with_collar" if collar else "without_collar"] += 1
        by_collar_type[str(collar_id) if collar and collar_id else "none"] += 1

        item_out = {
            "token_id": tid,
            "final_png_24": rel(out_png_path),
            "final_png_24_sha256": file_sha256(out_png_path),
            "base_preview_file": str(base_item["file"]),
            "base_origin_file_24": rel(base_origin_path),
            "source_tier": source_tier,
            "rarity_tier": rarity_tier,
            "rarity_type": rarity_type,
            "pattern": pattern,
            "palette_id": palette_id,
            "category": category,
            "collar": collar,
            "collar_id": collar_id,
            "collar_type": str(collar_id) if collar and collar_id else "none",
            "color_tuple": color_tuple,
            "variant_key": variant_key,
            "slots": slots,
            "layers_24": layers_24,
            "review_file": str(review_item.get("review_file")),
            "review_source_file": source_file_rel,
            "base_reference": {
                "base_pattern": base_item.get("pattern"),
                "base_palette_id": base_item.get("palette_id"),
                "base_collar": bool(base_item.get("collar")),
                "base_collar_id": base_item.get("collar_id"),
            },
            "attributes": build_attributes(
                pattern=pattern,
                palette_id=palette_id,
                collar=collar,
                collar_id=collar_id,
                rarity_tier=rarity_tier,
                rarity_type=rarity_type,
            ),
        }
        items_out.append(item_out)

    if len(items_out) != 1000:
        raise RuntimeError(f"Unexpected output item count: {len(items_out)}")
    if by_tier["rare"] != 98 or by_tier["superrare"] != 2 or by_tier["common"] != 900:
        raise RuntimeError(f"Unexpected rarity counts: {dict(by_tier)}")

    rare_part_inputs = {rt: rel(path) for rt, path in RARE_OVERLAY_BY_TYPE.items()}
    rare_part_hashes = {rt: file_sha256(path) for rt, path in RARE_OVERLAY_BY_TYPE.items()}

    out_obj = {
        "version": "final_1000_manifest_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "base_manifest": rel(args.base_manifest),
            "base_manifest_sha256": file_sha256(args.base_manifest),
            "review_manifest": rel(args.review_manifest),
            "review_manifest_sha256": file_sha256(args.review_manifest),
            "base_layer_24": rel(args.base_layer_24),
            "base_layer_24_sha256": file_sha256(args.base_layer_24),
            "rare_parts_24": rare_part_inputs,
            "rare_parts_24_sha256": rare_part_hashes,
            "superrare_collar_mode": args.superrare_collar_mode,
            "superrare_pattern": args.superrare_pattern,
            "superrare_palette": args.superrare_palette,
        },
        "counts": {
            "total": len(items_out),
            "by_rarity_tier": dict(by_tier),
            "by_rarity_type": dict(by_type),
            "by_pattern": dict(by_pattern),
            "by_palette_id": dict(by_palette),
            "by_collar": dict(by_collar_state),
            "by_collar_type": dict(by_collar_type),
        },
        "items": items_out,
    }
    args.out_manifest.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[final1000] out_dir={args.out_dir}")
    print(f"[final1000] out_manifest={args.out_manifest}")
    print(
        "[final1000] counts "
        f"common={by_tier['common']} rare={by_tier['rare']} superrare={by_tier['superrare']} "
        f"collar_with={by_collar_state['with_collar']} collar_without={by_collar_state['without_collar']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
