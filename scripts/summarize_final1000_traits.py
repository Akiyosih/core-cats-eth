#!/usr/bin/env python3
"""
Summarize trait distributions from final_1000_manifest.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "final_1000_manifest_v1.json"
DEFAULT_OUT = ROOT / "manifests" / "final_1000_trait_summary_v1.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def to_sorted_dict(counter: Counter) -> dict[str, int]:
    return {k: counter[k] for k in sorted(counter)}


def nested_sorted_dict(d: dict[str, Counter]) -> dict[str, dict[str, int]]:
    return {k: to_sorted_dict(d[k]) for k in sorted(d)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize final_1000_manifest traits.")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {args.manifest}")

    obj = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    if len(items) != 1000:
        raise RuntimeError(f"Expected 1000 items, got {len(items)}")

    by_pattern = Counter()
    by_palette = Counter()
    by_collar = Counter()
    by_tier = Counter()
    by_type = Counter()
    by_category = Counter()

    pattern_by_tier: dict[str, Counter] = defaultdict(Counter)
    palette_by_tier: dict[str, Counter] = defaultdict(Counter)
    collar_by_tier: dict[str, Counter] = defaultdict(Counter)
    type_by_tier: dict[str, Counter] = defaultdict(Counter)
    pattern_by_palette: dict[str, Counter] = defaultdict(Counter)
    type_by_collar: dict[str, Counter] = defaultdict(Counter)
    pattern_by_collar: dict[str, Counter] = defaultdict(Counter)

    for it in items:
        pattern = str(it["pattern"])
        palette = str(it["palette_id"])
        tier = str(it["rarity_tier"])
        rtype = str(it["rarity_type"])
        category = str(it.get("category", "unknown"))
        collar_state = "with_collar" if bool(it.get("collar")) else "without_collar"

        by_pattern[pattern] += 1
        by_palette[palette] += 1
        by_collar[collar_state] += 1
        by_tier[tier] += 1
        by_type[rtype] += 1
        by_category[category] += 1

        pattern_by_tier[tier][pattern] += 1
        palette_by_tier[tier][palette] += 1
        collar_by_tier[tier][collar_state] += 1
        type_by_tier[tier][rtype] += 1
        pattern_by_palette[palette][pattern] += 1
        type_by_collar[collar_state][rtype] += 1
        pattern_by_collar[collar_state][pattern] += 1

    out_obj = {
        "version": "final_1000_trait_summary_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest": rel(args.manifest),
        "total": len(items),
        "counts": {
            "by_pattern": to_sorted_dict(by_pattern),
            "by_palette_id": to_sorted_dict(by_palette),
            "by_collar": to_sorted_dict(by_collar),
            "by_rarity_tier": to_sorted_dict(by_tier),
            "by_rarity_type": to_sorted_dict(by_type),
            "by_category": to_sorted_dict(by_category),
        },
        "cross": {
            "pattern_by_rarity_tier": nested_sorted_dict(pattern_by_tier),
            "palette_by_rarity_tier": nested_sorted_dict(palette_by_tier),
            "collar_by_rarity_tier": nested_sorted_dict(collar_by_tier),
            "rarity_type_by_rarity_tier": nested_sorted_dict(type_by_tier),
            "pattern_by_palette_id": nested_sorted_dict(pattern_by_palette),
            "rarity_type_by_collar": nested_sorted_dict(type_by_collar),
            "pattern_by_collar": nested_sorted_dict(pattern_by_collar),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[summary-final1000] manifest={args.manifest}")
    print(f"[summary-final1000] out={args.out}")
    print(
        "[summary-final1000] "
        f"tier base={by_tier.get('base', 0)} rare={by_tier.get('rare', 0)} superrare={by_tier.get('superrare', 0)}"
    )
    print(
        "[summary-final1000] "
        f"collar with={by_collar.get('with_collar', 0)} without={by_collar.get('without_collar', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
