#!/usr/bin/env python3
"""
Validate final_1000_manifest and canonical 24x24 PNG outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "final_1000_manifest_v1.json"
DEFAULT_OUT = ROOT / "manifests" / "final_1000_validation_v1.json"

VALID_TIERS = {"common", "rare", "superrare"}
VALID_RARE_TYPES = {"odd_eyes", "red_nose", "blue_nose", "glasses", "sunglasses"}
VALID_SUPERRARE_TYPES = {"corelogo", "pinglogo"}
VALID_COLLAR_TYPES = {"none", "checkered_collar", "classic_red_collar"}
SUPERRARE_PATTERN = "superrare"
SUPERRARE_PALETTE = "superrare"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as rf:
        for chunk in iter(lambda: rf.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    b = path.read_bytes()
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Not a PNG file: {path}")
    if b[12:16] != b"IHDR":
        raise RuntimeError(f"PNG missing IHDR: {path}")
    return struct.unpack(">II", b[16:24])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate final_1000_manifest_v1.json")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--strict", action="store_true", help="Exit non-zero on validation errors.")
    return p.parse_args()


def add_error(errors: list[str], msg: str) -> None:
    errors.append(msg)


def main() -> int:
    args = parse_args()
    if not args.manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {args.manifest}")

    obj = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    errors: list[str] = []

    if len(items) != 1000:
        add_error(errors, f"Expected 1000 items, got {len(items)}")

    seen_tokens = set()
    by_tier = Counter()
    by_type = Counter()
    by_collar = Counter()
    by_collar_type = Counter()
    by_pattern = Counter()
    by_palette = Counter()

    for idx, it in enumerate(items):
        tid = it.get("token_id")
        if not isinstance(tid, int):
            add_error(errors, f"Item#{idx}: token_id is not int")
            continue
        if tid < 1 or tid > 1000:
            add_error(errors, f"token_id out of range: {tid}")
        if tid in seen_tokens:
            add_error(errors, f"Duplicate token_id: {tid}")
        seen_tokens.add(tid)

        tier = it.get("rarity_tier")
        if tier not in VALID_TIERS:
            add_error(errors, f"token {tid}: invalid rarity_tier={tier}")
            continue

        rtype = it.get("rarity_type")
        if tier == "common" and rtype != "none":
            add_error(errors, f"token {tid}: common token must have rarity_type=none (got {rtype})")
        if tier == "rare" and rtype not in VALID_RARE_TYPES:
            add_error(errors, f"token {tid}: invalid rare type={rtype}")
        if tier == "superrare" and rtype not in VALID_SUPERRARE_TYPES:
            add_error(errors, f"token {tid}: invalid superrare type={rtype}")

        pattern = it.get("pattern")
        palette = it.get("palette_id")
        if not isinstance(pattern, str) or not pattern:
            add_error(errors, f"token {tid}: invalid pattern")
        if not isinstance(palette, str) or not palette:
            add_error(errors, f"token {tid}: invalid palette_id")

        final_rel = it.get("final_png_24")
        if not isinstance(final_rel, str):
            add_error(errors, f"token {tid}: missing final_png_24")
        else:
            final_path = ROOT / final_rel
            if not final_path.exists():
                add_error(errors, f"token {tid}: missing final PNG file {final_rel}")
            else:
                try:
                    size = png_size(final_path)
                    if size != (24, 24):
                        add_error(errors, f"token {tid}: final PNG size is {size}, expected (24, 24)")
                except Exception as e:  # noqa: BLE001
                    add_error(errors, f"token {tid}: PNG parse error: {e}")

                expected_sha = it.get("final_png_24_sha256")
                if isinstance(expected_sha, str):
                    actual_sha = file_sha256(final_path)
                    if actual_sha != expected_sha:
                        add_error(errors, f"token {tid}: SHA mismatch for final PNG")
                else:
                    add_error(errors, f"token {tid}: missing final_png_24_sha256")

        collar = bool(it.get("collar"))
        collar_id = it.get("collar_id")
        collar_type = it.get("collar_type")
        if not collar and collar_id is not None:
            add_error(errors, f"token {tid}: collar=false but collar_id is not null")
        if collar and not isinstance(collar_id, str):
            add_error(errors, f"token {tid}: collar=true but collar_id is not a string")
        if not isinstance(collar_type, str) or collar_type not in VALID_COLLAR_TYPES:
            add_error(errors, f"token {tid}: invalid collar_type={collar_type}")
        if not collar and collar_type != "none":
            add_error(errors, f"token {tid}: collar=false but collar_type is not none")
        if collar and collar_type == "none":
            add_error(errors, f"token {tid}: collar=true but collar_type is none")
        if collar and isinstance(collar_id, str) and collar_type != collar_id:
            add_error(errors, f"token {tid}: collar_type and collar_id mismatch")

        if tier == "superrare":
            if pattern != SUPERRARE_PATTERN:
                add_error(errors, f"token {tid}: superrare pattern must be {SUPERRARE_PATTERN} (got {pattern})")
            if palette != SUPERRARE_PALETTE:
                add_error(
                    errors,
                    f"token {tid}: superrare palette_id must be {SUPERRARE_PALETTE} (got {palette})",
                )
            if collar:
                add_error(errors, f"token {tid}: superrare collar must be false")
            if collar_type != "none":
                add_error(errors, f"token {tid}: superrare collar_type must be none")

        attrs = it.get("attributes")
        if not isinstance(attrs, list):
            add_error(errors, f"token {tid}: attributes must be a list")
        else:
            trait_names = {a.get("trait_type") for a in attrs if isinstance(a, dict)}
            for req in ("Pattern", "Color Variation", "Collar", "Rarity Tier", "Rarity Type"):
                if req not in trait_names:
                    add_error(errors, f"token {tid}: missing required attribute {req}")
            attr_map = {}
            for a in attrs:
                if isinstance(a, dict) and "trait_type" in a and "value" in a:
                    attr_map[str(a["trait_type"])] = str(a["value"])
            if attr_map.get("Pattern") != str(pattern):
                add_error(errors, f"token {tid}: attribute Pattern mismatch")
            if attr_map.get("Color Variation") != str(palette):
                add_error(errors, f"token {tid}: attribute Color Variation mismatch")
            if attr_map.get("Collar") != str(collar_type):
                add_error(errors, f"token {tid}: attribute Collar mismatch")
            if attr_map.get("Rarity Tier") != str(tier):
                add_error(errors, f"token {tid}: attribute Rarity Tier mismatch")
            if attr_map.get("Rarity Type") != str(rtype):
                add_error(errors, f"token {tid}: attribute Rarity Type mismatch")

        by_tier[tier] += 1
        by_type[rtype] += 1
        by_collar["with_collar" if collar else "without_collar"] += 1
        by_collar_type[str(collar_type)] += 1
        by_pattern[pattern] += 1
        by_palette[palette] += 1

    expected_tokens = set(range(1, 1001))
    missing_tokens = sorted(expected_tokens - seen_tokens)
    extra_tokens = sorted(seen_tokens - expected_tokens)
    if missing_tokens:
        add_error(errors, f"Missing token_ids: {missing_tokens[:20]}")
    if extra_tokens:
        add_error(errors, f"Extra token_ids: {extra_tokens[:20]}")

    if by_tier.get("common", 0) != 900:
        add_error(errors, f"Expected common=900, got {by_tier.get('common', 0)}")
    if by_tier.get("rare", 0) != 98:
        add_error(errors, f"Expected rare=98, got {by_tier.get('rare', 0)}")
    if by_tier.get("superrare", 0) != 2:
        add_error(errors, f"Expected superrare=2, got {by_tier.get('superrare', 0)}")
    if by_type.get("none", 0) != 900:
        add_error(errors, f"Expected rarity_type none=900, got {by_type.get('none', 0)}")
    if by_type.get("corelogo", 0) != 1:
        add_error(errors, f"Expected rarity_type corelogo=1, got {by_type.get('corelogo', 0)}")
    if by_type.get("pinglogo", 0) != 1:
        add_error(errors, f"Expected rarity_type pinglogo=1, got {by_type.get('pinglogo', 0)}")
    if by_pattern.get(SUPERRARE_PATTERN, 0) != 2:
        add_error(errors, f"Expected pattern {SUPERRARE_PATTERN}=2, got {by_pattern.get(SUPERRARE_PATTERN, 0)}")
    if by_palette.get(SUPERRARE_PALETTE, 0) != 2:
        add_error(
            errors,
            f"Expected palette_id {SUPERRARE_PALETTE}=2, got {by_palette.get(SUPERRARE_PALETTE, 0)}",
        )

    ok = len(errors) == 0
    out_obj = {
        "version": "final_1000_validation_v1",
        "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest": rel(args.manifest),
        "ok": ok,
        "error_count": len(errors),
        "errors": errors,
        "counts": {
            "by_rarity_tier": dict(by_tier),
            "by_rarity_type": dict(by_type),
            "by_collar": dict(by_collar),
            "by_collar_type": dict(by_collar_type),
            "by_pattern": dict(by_pattern),
            "by_palette_id": dict(by_palette),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[validate-final1000] manifest={args.manifest}")
    print(f"[validate-final1000] out={args.out}")
    print(f"[validate-final1000] ok={ok} errors={len(errors)}")

    if args.strict and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
