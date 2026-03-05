#!/usr/bin/env python3
"""
Apply selected collar adjustments (wave1) to base1000 manifest.

This script updates:
- collar flags (`collar`, `collar_id`, `collar_overlay_file_24`)
- source preview file path (`file`, `filename`) for selected 7 tokens
- counts section for collar distribution
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE_MANIFEST = ROOT / "manifests" / "base1000_no_rare_latest.json"
DEFAULT_SELECTED_NONE_DIR = ROOT / "art" / "candidates" / "collar_adjustment_wave1" / "11_selected_none_to_checkered"
DEFAULT_SELECTED_CLASSIC_DIR = ROOT / "art" / "candidates" / "collar_adjustment_wave1" / "12_selected_classic_to_checkered"
DEFAULT_PREVIEW_MANIFEST = ROOT / "art" / "candidates" / "collar_adjustment_wave1" / "30_after_change_preview_7tokens" / "manifest.json"
DEFAULT_COPY_DST_DIR = ROOT / "art" / "selected" / "png_collar_adjusted_wave1"
CHECKERED_OVERLAY_24 = "art/parts/accessories/collar/checkered_collar.png"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply collar adjustment wave1 to base1000 manifest.")
    p.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    p.add_argument("--selected-none-dir", type=Path, default=DEFAULT_SELECTED_NONE_DIR)
    p.add_argument("--selected-classic-dir", type=Path, default=DEFAULT_SELECTED_CLASSIC_DIR)
    p.add_argument("--preview-manifest", type=Path, default=DEFAULT_PREVIEW_MANIFEST)
    p.add_argument("--copy-dst-dir", type=Path, default=DEFAULT_COPY_DST_DIR)
    p.add_argument("--expected-none-count", type=int, default=2)
    p.add_argument("--expected-classic-count", type=int, default=5)
    p.add_argument(
        "--expected-base-collar-true",
        type=int,
        default=402,
        help="Expected collar_true count in base1000 after applying this adjustment.",
    )
    p.add_argument(
        "--expected-base-collar-false",
        type=int,
        default=598,
        help="Expected collar_false count in base1000 after applying this adjustment.",
    )
    p.add_argument(
        "--expected-base-checkered",
        type=int,
        default=201,
        help="Expected checkered_collar count in base1000 after applying this adjustment.",
    )
    p.add_argument(
        "--expected-base-classic",
        type=int,
        default=201,
        help="Expected classic_red_collar count in base1000 after applying this adjustment.",
    )
    return p.parse_args()


def load_selected_ids(folder: Path) -> list[int]:
    ids: list[int] = []
    for p in sorted(folder.glob("*.png")):
        name = p.name
        if len(name) >= 6 and name[:4].isdigit() and name[4:6] == "__":
            ids.append(int(name[:4]))
    return ids


def require_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)


def main() -> int:
    args = parse_args()
    for required in [
        args.base_manifest,
        args.selected_none_dir,
        args.selected_classic_dir,
        args.preview_manifest,
    ]:
        require_exists(required)

    none_ids = load_selected_ids(args.selected_none_dir)
    classic_ids = load_selected_ids(args.selected_classic_dir)
    if len(none_ids) != args.expected_none_count:
        raise RuntimeError(f"Expected {args.expected_none_count} none->checkered tokens, got {len(none_ids)}")
    if len(classic_ids) != args.expected_classic_count:
        raise RuntimeError(f"Expected {args.expected_classic_count} classic->checkered tokens, got {len(classic_ids)}")

    all_ids = none_ids + classic_ids
    if len(set(all_ids)) != len(all_ids):
        raise RuntimeError("Duplicate token IDs across selected folders.")

    preview_obj = json.loads(args.preview_manifest.read_text(encoding="utf-8"))
    preview_items = preview_obj.get("items", [])
    after_preview_by_id: dict[int, Path] = {}
    for it in preview_items:
        tid = int(it["token_id"])
        ap = ROOT / str(it["after_preview"])
        require_exists(ap)
        after_preview_by_id[tid] = ap

    missing_preview = [tid for tid in all_ids if tid not in after_preview_by_id]
    if missing_preview:
        raise RuntimeError(f"Missing after_preview in preview manifest for token_ids={missing_preview}")

    base_obj = json.loads(args.base_manifest.read_text(encoding="utf-8"))
    items = base_obj.get("items", [])
    if len(items) != 1000:
        raise RuntimeError(f"Expected 1000 items in base manifest, got {len(items)}")
    item_by_id = {int(it["token_id"]): it for it in items}

    args.copy_dst_dir.mkdir(parents=True, exist_ok=True)

    for tid in all_ids:
        if tid not in item_by_id:
            raise RuntimeError(f"token_id not found in base manifest: {tid}")
        it = item_by_id[tid]
        if str(it.get("rarity_tier")) != "base":
            raise RuntimeError(f"token {tid} is not base tier")
        before_ct = str(it.get("collar_id")) if it.get("collar_id") else None
        if tid in none_ids and before_ct is not None:
            raise RuntimeError(f"token {tid}: expected no collar before change")
        if tid in classic_ids and before_ct != "classic_red_collar":
            raise RuntimeError(f"token {tid}: expected classic_red_collar before change, got {before_ct}")

        src_preview = after_preview_by_id[tid]
        dst_name = f"{tid:04d}__{it['pattern']}__{it['palette_id']}__collar_checkered_collar.png"
        dst_preview = args.copy_dst_dir / dst_name
        shutil.copy2(src_preview, dst_preview)

        it["file"] = rel(dst_preview)
        it["filename"] = dst_name
        it["collar"] = True
        it["collar_id"] = "checkered_collar"
        it["collar_overlay_file_24"] = CHECKERED_OVERLAY_24

    # Recompute collar counts from full item set.
    collar_true = 0
    collar_false = 0
    checkered = 0
    classic = 0
    for it in items:
        collar = bool(it.get("collar"))
        cid = it.get("collar_id")
        if collar:
            collar_true += 1
            if cid == "checkered_collar":
                checkered += 1
            elif cid == "classic_red_collar":
                classic += 1
        else:
            collar_false += 1

    counts = base_obj.setdefault("counts", {})
    counts["collar_true"] = collar_true
    counts["collar_false"] = collar_false
    counts["checkered_collar"] = checkered
    counts["classic_red_collar"] = classic

    if (
        collar_true != args.expected_base_collar_true
        or collar_false != args.expected_base_collar_false
        or checkered != args.expected_base_checkered
        or classic != args.expected_base_classic
    ):
        raise RuntimeError(
            "Post-adjustment counts mismatch: "
            f"collar_true={collar_true} collar_false={collar_false} checkered={checkered} classic={classic}"
        )

    inputs = base_obj.setdefault("inputs", {})
    inputs["collar_adjustment_wave1"] = {
        "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "none_to_checkered_token_ids": sorted(none_ids),
        "classic_to_checkered_token_ids": sorted(classic_ids),
        "preview_manifest": rel(args.preview_manifest),
    }
    base_obj["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if base_obj.get("version") == "base1000_no_rare_v1":
        base_obj["version"] = "base1000_no_rare_v1_1"

    args.base_manifest.write_text(json.dumps(base_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[apply-collar-adjustment-wave1] base_manifest={args.base_manifest}")
    print(f"[apply-collar-adjustment-wave1] none_to_checkered={sorted(none_ids)}")
    print(f"[apply-collar-adjustment-wave1] classic_to_checkered={sorted(classic_ids)}")
    print(
        "[apply-collar-adjustment-wave1] "
        f"collar_true={collar_true} collar_false={collar_false} "
        f"checkered={checkered} classic={classic}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
