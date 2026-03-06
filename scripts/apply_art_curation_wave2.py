#!/usr/bin/env python3
"""
Apply art replacement and metadata cleanup decisions after manual review (wave2).

Outputs:
- manifests/base1000_no_rare_latest.json
- manifests/final1000_review_manifest_v1.json
- art/candidates/art_curation_wave2_20260307/png/*
- art/review/final1000_preview_v1/png/0750__base.png
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURATION = ROOT / "manifests" / "art_curation_wave2_20260307.json"
DEFAULT_GENERATED = ROOT / "manifests" / "generated.jsonl"
DEFAULT_BASE = ROOT / "manifests" / "base1000_no_rare_latest.json"
DEFAULT_REVIEW = ROOT / "manifests" / "final1000_review_manifest_v1.json"
DEFAULT_BASE_LAYER = ROOT / "art" / "base" / "base.png"
DEFAULT_COLLAR_DIR = ROOT / "art" / "parts" / "accessories" / "collar"
DEFAULT_RARE_DIR = ROOT / "art" / "parts" / "rare"
DEFAULT_REVIEW_OUT_DIR = ROOT / "art" / "review" / "final1000_preview_v1" / "png"
SCALE = 32


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def fit_to_size(img: Image.Image, target_size: tuple[int, int], label: str) -> Image.Image:
    if img.size == target_size:
        return img
    tw, th = target_size
    sw, sh = img.size
    if tw % sw == 0 and th % sh == 0 and (tw // sw) == (th // sh):
        return img.resize(target_size, Image.NEAREST)
    raise RuntimeError(f"Cannot fit {label} size {img.size} -> {target_size}")


def load_generated_map(path: Path) -> dict[str, dict]:
    out = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            out[str(rec["file"])] = rec
    return out


def build_preview(pattern_24: Path, base_layer: Image.Image, *, collar_id: str | None, rare_type: str | None) -> Image.Image:
    canvas = fit_to_size(Image.open(pattern_24).convert("RGBA"), base_layer.size, f"pattern {pattern_24}")
    canvas = canvas.copy()
    canvas.alpha_composite(base_layer)
    if collar_id:
        collar = fit_to_size(Image.open(DEFAULT_COLLAR_DIR / f"{collar_id}.png").convert("RGBA"), base_layer.size, f"collar {collar_id}")
        canvas.alpha_composite(collar)
    if rare_type:
        rare = fit_to_size(Image.open(DEFAULT_RARE_DIR / f"{rare_type}.png").convert("RGBA"), base_layer.size, f"rare {rare_type}")
        canvas.alpha_composite(rare)
    return canvas


def save_preview(preview_24: Image.Image, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    preview_24.resize((preview_24.width * SCALE, preview_24.height * SCALE), Image.NEAREST).save(
        out_path, format="PNG", optimize=False
    )


def update_counts(base_obj: dict) -> None:
    items = base_obj["items"]
    src_counts = Counter(r["source_kind"] for r in items)
    collar_counts = Counter(r["collar_id"] for r in items if r["collar"])
    base_obj["counts"] = {
        "total": len(items),
        "base600": src_counts.get("base600", 0),
        "collar400": src_counts.get("collar400", 0),
        "collar_true": sum(1 for r in items if r["collar"]),
        "collar_false": sum(1 for r in items if not r["collar"]),
        "rare": sum(1 for r in items if r["rarity_tier"] == "rare"),
        "superrare": sum(1 for r in items if r["rarity_tier"] == "superrare"),
        "checkered_collar": collar_counts.get("checkered_collar", 0),
        "classic_red_collar": collar_counts.get("classic_red_collar", 0),
    }


def update_review_counts(review_obj: dict) -> None:
    items = review_obj["items"]
    counts = Counter(it["source_tier"] for it in items)
    collar_counter = Counter()
    for it in items:
        if it["source_tier"] in {"rare", "superrare"}:
            collar_counter["with_collar" if it["collar"] else "without_collar"] += 1
    review_obj["counts"] = {
        "total": len(items),
        "base": counts["base"],
        "rare": counts["rare"],
        "superrare": counts["superrare"],
        "modified_total": counts["rare"] + counts["superrare"],
        "modified_with_collar": collar_counter["with_collar"],
        "modified_without_collar": collar_counter["without_collar"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply art curation wave2 to base/review manifests.")
    parser.add_argument("--curation", type=Path, default=DEFAULT_CURATION)
    parser.add_argument("--generated", type=Path, default=DEFAULT_GENERATED)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()

    curation = load_json(args.curation)
    generated_map = load_generated_map(args.generated)
    base_obj = load_json(args.base)
    review_obj = load_json(args.review)

    base_items = {int(it["token_id"]): it for it in base_obj["items"]}
    review_items = {int(it["token_id"]): it for it in review_obj["items"]}

    for upd in curation.get("pattern_updates", []):
        target_pattern = str(upd["pattern"])
        for tid in upd.get("token_ids", []):
            tid = int(tid)
            if tid not in base_items:
                raise RuntimeError(f"token_id not found in base manifest: {tid}")
            base_items[tid]["pattern"] = target_pattern

    preview_dir = ROOT / "art" / "candidates" / curation["version"] / "png"
    review_out_dir = DEFAULT_REVIEW_OUT_DIR
    base_layer = Image.open(DEFAULT_BASE_LAYER).convert("RGBA")

    for repl in curation.get("replacements", []):
        tid = int(repl["token_id"])
        generated_rel = str(repl["generated_file_24"])
        generated_path = ROOT / generated_rel
        if generated_rel not in generated_map:
            raise RuntimeError(f"Generated record not found: {generated_rel}")
        gen = generated_map[generated_rel]
        base_item = base_items[tid]
        review_item = review_items[tid]

        collar_id = base_item.get("collar_id") if base_item.get("collar") else None
        if "keep_collar_id" in repl:
            collar_id = str(repl["keep_collar_id"])
            base_item["collar"] = True
            base_item["collar_id"] = collar_id
            base_item["collar_overlay_file_24"] = f"art/parts/accessories/collar/{collar_id}.png"

        filename = Path(generated_rel).name
        base_filename = filename
        preview_name = filename if not collar_id else filename.replace(".png", f"__collar_{collar_id}.png")

        base_preview_rel = rel(preview_dir / preview_name)
        review_preview_rel = rel(review_out_dir / f"{tid:04d}__base.png")

        base_preview_img = build_preview(generated_path, base_layer, collar_id=collar_id, rare_type=None)
        save_preview(base_preview_img, preview_dir / preview_name)
        save_preview(base_preview_img, review_out_dir / f"{tid:04d}__base.png")

        base_item["file"] = base_preview_rel
        base_item["filename"] = preview_name
        base_item["base_filename"] = base_filename
        base_item["pattern"] = str(gen["pattern"])
        base_item["palette_id"] = str(gen["palette_id"])
        base_item["color_tuple"] = list(gen.get("color_tuple") or [])
        base_item["variant_key"] = str(gen["variant_key"])
        base_item["slots"] = int(gen["slots"])
        base_item["category"] = str(gen["category"])
        base_item["origin_file_24"] = generated_rel

        if str(repl["source_kind"]) == "base":
            review_item["source_tier"] = "base"
            review_item["rarity_type"] = None
            review_item["source_file"] = base_preview_rel
            review_item["base_file"] = base_preview_rel
            review_item["review_file"] = review_preview_rel
            review_item["collar"] = bool(base_item["collar"])
            review_item["collar_id"] = base_item.get("collar_id")
        else:
            rare_type = str(repl["rarity_type"])
            rare_preview_name = f"{tid:04d}__{Path(preview_name).stem}__rare_{rare_type}.png"
            rare_preview_rel = rel(preview_dir / rare_preview_name)
            rare_review_rel = rel(review_out_dir / f"{tid:04d}__rare_{rare_type}.png")
            rare_preview_img = build_preview(generated_path, base_layer, collar_id=collar_id, rare_type=rare_type)
            save_preview(rare_preview_img, preview_dir / rare_preview_name)
            save_preview(rare_preview_img, review_out_dir / f"{tid:04d}__rare_{rare_type}.png")

            review_item["source_tier"] = "rare"
            review_item["rarity_type"] = rare_type
            review_item["source_file"] = rare_preview_rel
            review_item["base_file"] = base_preview_rel
            review_item["review_file"] = rare_review_rel
            review_item["collar"] = True
            review_item["collar_id"] = collar_id

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base_obj["created_at"] = now
    base_obj["version"] = "base1000_no_rare_v1_3"
    base_obj.setdefault("inputs", {})
    base_obj["inputs"]["art_curation_wave2"] = rel(args.curation)
    base_obj["inputs"]["art_curation_wave2_applied_at"] = now
    update_counts(base_obj)

    review_obj["created_at"] = now
    review_obj["version"] = "final1000_review_v1_2"
    review_obj.setdefault("inputs", {})
    review_obj["inputs"]["art_curation_wave2"] = rel(args.curation)
    update_review_counts(review_obj)

    dump_json(args.base, base_obj)
    dump_json(args.review, review_obj)

    updated_tokens = sorted({int(t) for upd in curation.get("pattern_updates", []) for t in upd.get("token_ids", [])})
    print(f"[art-curation-wave2] base={args.base}")
    print(f"[art-curation-wave2] review={args.review}")
    print(f"[art-curation-wave2] pattern_updates={len(updated_tokens)} replacements={len(curation.get('replacements', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
