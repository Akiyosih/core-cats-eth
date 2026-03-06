#!/usr/bin/env python3
"""
Apply the finalized token ordering from order_preview_wave1 to base/review manifests.

This rewrites token_id assignments so that preview order becomes canonical token order.
It also renames canonical review preview files under art/review/final1000_preview_v1/png.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "manifests" / "base1000_no_rare_latest.json"
DEFAULT_REVIEW = ROOT / "manifests" / "final1000_review_manifest_v1.json"
DEFAULT_ORDERED = ROOT / "art" / "review" / "order_preview_wave1" / "ordered_manifest.json"
DEFAULT_MAPPING_OUT = ROOT / "manifests" / "token_reorder_wave1_20260307.json"
DEFAULT_REVIEW_DIR = ROOT / "art" / "review" / "final1000_preview_v1" / "png"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def rebuild_base_counts(items: list[dict]) -> dict:
    src_counts = Counter(r["source_kind"] for r in items)
    collar_counts = Counter(r["collar_id"] for r in items if r["collar"])
    return {
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


def rebuild_review_counts(items: list[dict]) -> dict:
    counts = Counter(it["source_tier"] for it in items)
    collar_counter = Counter()
    for it in items:
        if it["source_tier"] in {"rare", "superrare"}:
            collar_counter["with_collar" if it["collar"] else "without_collar"] += 1
    return {
        "total": len(items),
        "base": counts["base"],
        "rare": counts["rare"],
        "superrare": counts["superrare"],
        "modified_total": counts["rare"] + counts["superrare"],
        "modified_with_collar": collar_counter["with_collar"],
        "modified_without_collar": collar_counter["without_collar"],
    }


def review_dest_name(new_tid: int, old_review_rel: str) -> str:
    name = Path(old_review_rel).name
    parts = name.split("__", 1)
    suffix = parts[1] if len(parts) == 2 else name
    return f"{new_tid:04d}__{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply finalized token reordering.")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--ordered", type=Path, default=DEFAULT_ORDERED)
    parser.add_argument("--mapping-out", type=Path, default=DEFAULT_MAPPING_OUT)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    args = parser.parse_args()

    base_obj = load_json(args.base)
    review_obj = load_json(args.review)
    ordered_obj = load_json(args.ordered)

    ordered_items = ordered_obj["items"]
    if len(ordered_items) != 1000:
        raise RuntimeError(f"Expected 1000 ordered items, got {len(ordered_items)}")

    old_to_new: dict[int, int] = {}
    new_to_old: dict[int, int] = {}
    for row in ordered_items:
        new_tid = int(row["order_index"])
        old_tid = int(row["token_id"])
        if old_tid in old_to_new:
            raise RuntimeError(f"Duplicate old token in ordered manifest: {old_tid}")
        if new_tid in new_to_old:
            raise RuntimeError(f"Duplicate order_index in ordered manifest: {new_tid}")
        old_to_new[old_tid] = new_tid
        new_to_old[new_tid] = old_tid

    if set(old_to_new) != set(range(1, 1001)):
        missing = sorted(set(range(1, 1001)) - set(old_to_new))
        extra = sorted(set(old_to_new) - set(range(1, 1001)))
        raise RuntimeError(f"Ordered manifest token coverage mismatch missing={missing[:10]} extra={extra[:10]}")

    base_map = {int(it["token_id"]): it for it in base_obj["items"]}
    review_map = {int(it["token_id"]): it for it in review_obj["items"]}

    tmp_review_dir = args.review_dir.parent / (args.review_dir.name + ".reorder_tmp")
    if tmp_review_dir.exists():
        shutil.rmtree(tmp_review_dir)
    tmp_review_dir.mkdir(parents=True, exist_ok=True)

    new_base_items = []
    new_review_items = []
    mapping_rows = []

    for new_tid in range(1, 1001):
        old_tid = new_to_old[new_tid]
        base_item = copy.deepcopy(base_map[old_tid])
        review_item = copy.deepcopy(review_map[old_tid])

        old_review_rel = str(review_item["review_file"])
        old_review_path = ROOT / old_review_rel
        if not old_review_path.exists():
            raise FileNotFoundError(f"Missing review preview file: {old_review_rel}")
        new_review_name = review_dest_name(new_tid, old_review_rel)
        new_review_path = tmp_review_dir / new_review_name
        final_review_path = args.review_dir / new_review_name
        shutil.copy2(old_review_path, new_review_path)

        base_item["token_id"] = new_tid
        review_item["token_id"] = new_tid
        review_item["review_file"] = rel(final_review_path)

        new_base_items.append(base_item)
        new_review_items.append(review_item)
        mapping_rows.append({
            "new_token_id": new_tid,
            "old_token_id": old_tid,
            "pattern": base_item["pattern"],
            "category": base_item["category"],
            "palette_id": base_item["palette_id"],
            "rarity_tier": "superrare" if review_item["source_tier"] == "superrare" else ("rare" if review_item["source_tier"] == "rare" else "common"),
            "rarity_type": review_item["rarity_type"] or "none",
        })

    # replace canonical review preview directory atomically enough for local use
    backup_dir = args.review_dir.parent / (args.review_dir.name + ".pre_reorder_backup")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    args.review_dir.rename(backup_dir)
    tmp_review_dir.rename(args.review_dir)
    shutil.rmtree(backup_dir)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base_obj["items"] = new_base_items
    base_obj["created_at"] = now
    base_obj["version"] = "base1000_no_rare_v1_4"
    base_obj.setdefault("inputs", {})
    base_obj["inputs"]["token_reorder_wave1"] = rel(args.mapping_out)
    base_obj["inputs"]["token_reorder_wave1_applied_at"] = now
    base_obj["counts"] = rebuild_base_counts(new_base_items)

    review_obj["items"] = new_review_items
    review_obj["created_at"] = now
    review_obj["version"] = "final1000_review_v1_3"
    review_obj.setdefault("inputs", {})
    review_obj["inputs"]["token_reorder_wave1"] = rel(args.mapping_out)
    review_obj["counts"] = rebuild_review_counts(new_review_items)

    dump_json(args.base, base_obj)
    dump_json(args.review, review_obj)
    dump_json(args.mapping_out, {
        "version": "token_reorder_wave1_20260307",
        "created_at": now,
        "source_ordered_manifest": rel(args.ordered),
        "rows": mapping_rows,
    })

    print(f"[token-reorder-wave1] base={args.base}")
    print(f"[token-reorder-wave1] review={args.review}")
    print(f"[token-reorder-wave1] mapping={args.mapping_out}")
    print(f"[token-reorder-wave1] review_dir={args.review_dir}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
