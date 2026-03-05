#!/usr/bin/env python3
"""
Audit consistency between final 24x24 outputs and review preview PNGs.

Rule:
- For each token, load final PNG (24x24)
- Load corresponding review PNG (typically 768x768)
- If review size is integer-multiple of 24, downscale to 24 with nearest-neighbor
- Compare RGBA pixel-perfect equality
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "final_1000_manifest_v1.json"
DEFAULT_OUT = ROOT / "manifests" / "final_1000_preview_consistency_v1.json"
TARGET_SIZE = (24, 24)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit final24 vs review preview consistency.")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--strict", action="store_true", help="Exit non-zero if mismatches/errors exist.")
    return p.parse_args()


def normalize_review_to_24(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    if img.size == TARGET_SIZE:
        return img
    rw, rh = img.size
    tw, th = TARGET_SIZE
    if rw % tw != 0 or rh % th != 0:
        raise RuntimeError(f"Review size is not multiple of 24: {img.size}")
    fx = rw // tw
    fy = rh // th
    if fx != fy:
        raise RuntimeError(f"Review scale is not isotropic: {img.size}")
    return img.resize(TARGET_SIZE, Image.NEAREST)


def main() -> int:
    args = parse_args()
    if not args.manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {args.manifest}")

    obj = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    if len(items) != 1000:
        raise RuntimeError(f"Expected 1000 items in manifest, got {len(items)}")

    checked = 0
    matched = 0
    mismatches = []
    errors = []

    for it in items:
        tid = int(it["token_id"])
        final_path = ROOT / str(it["final_png_24"])
        review_path = ROOT / str(it["review_file"])

        if not final_path.exists():
            errors.append({"token_id": tid, "error": f"Missing final file: {rel(final_path)}"})
            continue
        if not review_path.exists():
            errors.append({"token_id": tid, "error": f"Missing review file: {rel(review_path)}"})
            continue

        checked += 1
        try:
            final_img = Image.open(final_path).convert("RGBA")
            review_img = Image.open(review_path).convert("RGBA")
            review_24 = normalize_review_to_24(review_img)
        except Exception as e:  # noqa: BLE001
            errors.append({"token_id": tid, "error": str(e)})
            continue

        if final_img.size != TARGET_SIZE:
            errors.append({"token_id": tid, "error": f"Final image size is not 24x24: {final_img.size}"})
            continue

        diff = ImageChops.difference(final_img, review_24)
        if diff.getbbox() is None:
            matched += 1
            continue

        mismatches.append(
            {
                "token_id": tid,
                "final_png_24": str(it["final_png_24"]),
                "review_file": str(it["review_file"]),
                "rarity_tier": str(it.get("rarity_tier")),
                "rarity_type": str(it.get("rarity_type")),
            }
        )

    ok = len(mismatches) == 0 and len(errors) == 0 and checked == 1000 and matched == 1000
    out_obj = {
        "version": "final_1000_preview_consistency_v1",
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest": rel(args.manifest),
        "ok": ok,
        "checked": checked,
        "matched": matched,
        "mismatch_count": len(mismatches),
        "error_count": len(errors),
        "mismatches": mismatches[:200],
        "errors": errors[:200],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[audit-final-vs-review] manifest={args.manifest}")
    print(f"[audit-final-vs-review] out={args.out}")
    print(
        "[audit-final-vs-review] "
        f"ok={ok} checked={checked} matched={matched} mismatches={len(mismatches)} errors={len(errors)}"
    )

    if args.strict and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
