#!/usr/bin/env python3
"""
Build canonical base-1000 manifest (no rare traits yet).

Inputs:
- manifests/selected_wave3_20250820_215950.json (base 600)
- manifests/collar_wave1_selection_prune_*.json (selected collar 400)

Output:
- manifests/base1000_no_rare_<timestamp>.json
- manifests/base1000_no_rare_latest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE600 = ROOT / "manifests" / "selected_wave3_20250820_215950.json"
DEFAULT_COLLAR400 = ROOT / "manifests" / "collar_wave1_selection_prune_20260305_115544.json"
DEFAULT_OUT_DIR = ROOT / "manifests"

COLLAR_NAME_RE = re.compile(r"^(?P<base_stem>.+)__collar_(?P<collar_id>.+)\.png$", re.IGNORECASE)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as rf:
        for chunk in iter(lambda: rf.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build base 1000 manifest (no rare).")
    p.add_argument("--base600", type=Path, default=DEFAULT_BASE600)
    p.add_argument("--collar400", type=Path, default=DEFAULT_COLLAR400)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return p.parse_args()


def build_records(base600: dict, collar400: dict) -> List[dict]:
    items600 = base600.get("items", [])
    if len(items600) != 600:
        raise RuntimeError(f"Expected 600 base items, got {len(items600)}")

    by_filename: Dict[str, dict] = {it["filename"]: it for it in items600}
    if len(by_filename) != 600:
        raise RuntimeError("Duplicate filename found in base600 items")

    records: List[dict] = []

    # 1) base 600
    for it in items600:
        records.append(
            {
                "token_id": None,  # assigned later
                "source_kind": "base600",
                "file": it["file"],  # preview-sized selected image path
                "filename": it["filename"],
                "base_filename": it["filename"],
                "pattern": it.get("pattern"),
                "palette_id": it.get("palette_id"),
                "color_tuple": it.get("color_tuple"),
                "variant_key": it.get("variant_key"),
                "slots": it.get("slots"),
                "category": it.get("category"),
                "origin_file_24": it.get("origin_file"),  # canonical 24x24 source
                "collar": False,
                "collar_id": None,
                "collar_overlay_file_24": None,
                "rarity_tier": "base",
                "rarity_type": None,
            }
        )

    # 2) collar 400
    remaining = collar400.get("remaining_files", [])
    after_count = collar400.get("after_count")
    if after_count is not None and after_count != len(remaining):
        raise RuntimeError(f"collar400 mismatch: after_count={after_count}, remaining={len(remaining)}")
    if len(remaining) != 400:
        raise RuntimeError(f"Expected 400 collar files, got {len(remaining)}")

    seen = set()
    for rel_path in sorted(remaining):
        p = Path(rel_path)
        filename = p.name
        m = COLLAR_NAME_RE.match(filename)
        if not m:
            raise RuntimeError(f"Unexpected collar filename format: {filename}")
        base_filename = f"{m.group('base_stem')}.png"
        collar_id = m.group("collar_id")
        if base_filename not in by_filename:
            raise RuntimeError(f"Base filename not found for collar file: {filename}")
        if filename in seen:
            raise RuntimeError(f"Duplicate collar filename: {filename}")
        seen.add(filename)

        base = by_filename[base_filename]
        records.append(
            {
                "token_id": None,  # assigned later
                "source_kind": "collar400",
                "file": rel_path,  # preview-sized selected collar candidate path
                "filename": filename,
                "base_filename": base_filename,
                "pattern": base.get("pattern"),
                "palette_id": base.get("palette_id"),
                "color_tuple": base.get("color_tuple"),
                "variant_key": base.get("variant_key"),
                "slots": base.get("slots"),
                "category": base.get("category"),
                "origin_file_24": base.get("origin_file"),  # base 24x24
                "collar": True,
                "collar_id": collar_id,
                "collar_overlay_file_24": f"art/parts/accessories/collar/{collar_id}.png",
                "rarity_tier": "base",
                "rarity_type": None,
            }
        )

    if len(records) != 1000:
        raise RuntimeError(f"Expected total 1000 records, got {len(records)}")

    # Deterministic token assignment:
    # - first 600 in the original base selection order
    # - then 400 collar records in filename order
    for token_id, rec in enumerate(records, start=1):
        rec["token_id"] = token_id

    return records


def main() -> int:
    args = parse_args()
    if not args.base600.exists():
        raise FileNotFoundError(f"Missing base600 manifest: {args.base600}")
    if not args.collar400.exists():
        raise FileNotFoundError(f"Missing collar400 manifest: {args.collar400}")

    base600 = load_json(args.base600)
    collar400 = load_json(args.collar400)
    records = build_records(base600, collar400)

    src_counts = Counter(r["source_kind"] for r in records)
    collar_counts = Counter(r["collar_id"] for r in records if r["collar"])

    out = {
        "version": "base1000_no_rare_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "base600_manifest": rel(args.base600),
            "base600_manifest_sha256": file_sha256(args.base600),
            "collar400_selection_manifest": rel(args.collar400),
            "collar400_selection_manifest_sha256": file_sha256(args.collar400),
            "rule": "token_id=1..600 from base600 order, 601..1000 from collar400 filename order",
        },
        "counts": {
            "total": len(records),
            "base600": src_counts.get("base600", 0),
            "collar400": src_counts.get("collar400", 0),
            "collar_true": sum(1 for r in records if r["collar"]),
            "collar_false": sum(1 for r in records if not r["collar"]),
            "rare": sum(1 for r in records if r["rarity_tier"] == "rare"),
            "superrare": sum(1 for r in records if r["rarity_tier"] == "superrare"),
            "checkered_collar": collar_counts.get("checkered_collar", 0),
            "classic_red_collar": collar_counts.get("classic_red_collar", 0),
        },
        "items": records,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = args.out_dir / f"base1000_no_rare_{stamp}.json"
    latest_path = args.out_dir / "base1000_no_rare_latest.json"

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[base1000] wrote={rel(out_path)}")
    print(f"[base1000] latest={rel(latest_path)}")
    print(f"[base1000] total={out['counts']['total']} base600={out['counts']['base600']} collar400={out['counts']['collar400']}")
    print(f"[base1000] collar checkered={out['counts']['checkered_collar']} classic_red={out['counts']['classic_red_collar']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
