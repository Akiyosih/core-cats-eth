#!/usr/bin/env python3
"""
Generate visual previews for selected collar adjustment tokens.

Usage (Windows venv with Pillow):
  .\\.venv\\Scripts\\python.exe .\\scripts\\preview_collar_adjustment_wave1.py
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MANIFEST = ROOT / "manifests" / "final_1000_manifest_v1.json"
DEFAULT_SELECTED_NONE = ROOT / "art" / "candidates" / "collar_adjustment_wave1" / "11_selected_none_to_checkered"
DEFAULT_SELECTED_CLASSIC = ROOT / "art" / "candidates" / "collar_adjustment_wave1" / "12_selected_classic_to_checkered"
DEFAULT_OUT = ROOT / "art" / "candidates" / "collar_adjustment_wave1" / "30_after_change_preview_7tokens"
DEFAULT_BASE_LAYER = ROOT / "art" / "base" / "base.png"
DEFAULT_CHECKERED = ROOT / "art" / "parts" / "accessories" / "collar" / "checkered_collar.png"

TOKEN_RE = re.compile(r"^(?P<token>\d{4})__")


@dataclass(frozen=True)
class SelectedSets:
    none_to_checkered: list[int]
    classic_to_checkered: list[int]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Preview collar adjustment selections.")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--selected-none-dir", type=Path, default=DEFAULT_SELECTED_NONE)
    p.add_argument("--selected-classic-dir", type=Path, default=DEFAULT_SELECTED_CLASSIC)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--base-layer", type=Path, default=DEFAULT_BASE_LAYER)
    p.add_argument("--checkered-overlay", type=Path, default=DEFAULT_CHECKERED)
    p.add_argument("--none-count", type=int, default=2)
    p.add_argument("--classic-count", type=int, default=5)
    p.add_argument("--scale", type=int, default=16, help="Fallback scale for after image when preview size is not integer multiple.")
    return p.parse_args()


def load_token_ids(folder: Path) -> list[int]:
    ids: list[int] = []
    for p in sorted(folder.glob("*.png")):
        m = TOKEN_RE.match(p.name)
        if not m:
            continue
        ids.append(int(m.group("token")))
    return ids


def load_selected_sets(none_dir: Path, classic_dir: Path) -> SelectedSets:
    if not none_dir.exists():
        raise FileNotFoundError(f"Missing selected folder: {none_dir}")
    if not classic_dir.exists():
        raise FileNotFoundError(f"Missing selected folder: {classic_dir}")
    return SelectedSets(
        none_to_checkered=load_token_ids(none_dir),
        classic_to_checkered=load_token_ids(classic_dir),
    )


def upscale_to_preview(after24: Image.Image, preview_size: tuple[int, int], fallback_scale: int) -> Image.Image:
    tw, th = preview_size
    if tw % 24 == 0 and th % 24 == 0 and tw // 24 == th // 24:
        return after24.resize(preview_size, Image.NEAREST)
    return after24.resize((24 * fallback_scale, 24 * fallback_scale), Image.NEAREST)


def make_compare(before_img: Image.Image, after_img: Image.Image, title: str) -> Image.Image:
    pad = 24
    gap = 24
    header_h = 36
    footer_h = 28
    bw, bh = before_img.size
    aw, ah = after_img.size
    h = max(bh, ah)
    w = pad + bw + gap + aw + pad
    canvas = Image.new("RGBA", (w, pad + header_h + h + footer_h), (20, 26, 32, 255))
    canvas.alpha_composite(before_img, (pad, pad + header_h))
    canvas.alpha_composite(after_img, (pad + bw + gap, pad + header_h))
    d = ImageDraw.Draw(canvas)
    d.text((pad, pad + 6), "BEFORE", fill=(230, 235, 245, 255))
    d.text((pad + bw + gap, pad + 6), "AFTER (checkered_collar)", fill=(230, 235, 245, 255))
    d.text((pad, pad + header_h + h + 6), title, fill=(230, 235, 245, 255))
    return canvas


def main() -> int:
    args = parse_args()

    for required in [args.manifest, args.base_layer, args.checkered_overlay]:
        if not required.exists():
            raise FileNotFoundError(f"Missing required file: {required}")

    selected = load_selected_sets(args.selected_none_dir, args.selected_classic_dir)
    if len(selected.none_to_checkered) != args.none_count:
        raise RuntimeError(
            f"Expected {args.none_count} tokens in {args.selected_none_dir}, got {len(selected.none_to_checkered)}"
        )
    if len(selected.classic_to_checkered) != args.classic_count:
        raise RuntimeError(
            f"Expected {args.classic_count} tokens in {args.selected_classic_dir}, got {len(selected.classic_to_checkered)}"
        )

    all_ids = selected.none_to_checkered + selected.classic_to_checkered
    if len(set(all_ids)) != len(all_ids):
        raise RuntimeError("Duplicate token IDs across selected folders.")

    obj = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    item_by_id = {int(it["token_id"]): it for it in items}

    out_before24 = args.out_dir / "before_24"
    out_after24 = args.out_dir / "after_24"
    out_after_preview = args.out_dir / "after_preview"
    out_compare = args.out_dir / "compare"
    for d in [args.out_dir, out_before24, out_after24, out_after_preview, out_compare]:
        d.mkdir(parents=True, exist_ok=True)
    for d in [out_before24, out_after24, out_after_preview, out_compare]:
        for p in d.glob("*.png"):
            p.unlink()

    base_layer = Image.open(args.base_layer).convert("RGBA")
    checkered = Image.open(args.checkered_overlay).convert("RGBA")

    records: list[dict] = []

    for tid in all_ids:
        if tid not in item_by_id:
            raise RuntimeError(f"Selected token not found in manifest: {tid}")
        it = item_by_id[tid]
        tier = str(it.get("rarity_tier"))
        if tier not in {"common", "base"}:
            raise RuntimeError(f"Selected token {tid} tier={tier}, expected common/base")

        before24 = Image.open(ROOT / str(it["final_png_24"])).convert("RGBA")
        before_preview = Image.open(ROOT / str(it["review_file"])).convert("RGBA")
        origin24 = Image.open(ROOT / str(it["base_origin_file_24"])).convert("RGBA")

        # Compose new 24x24 target with checkered collar.
        after24 = origin24.copy()
        after24.alpha_composite(base_layer)
        after24.alpha_composite(checkered)

        after_preview = upscale_to_preview(after24, before_preview.size, args.scale)

        b24_name = f"{tid:04d}__before.png"
        a24_name = f"{tid:04d}__after_checkered.png"
        apv_name = f"{tid:04d}__after_checkered_preview.png"
        cmp_name = f"{tid:04d}__compare.png"

        before24.save(out_before24 / b24_name, format="PNG", optimize=False)
        after24.save(out_after24 / a24_name, format="PNG", optimize=False)
        after_preview.save(out_after_preview / apv_name, format="PNG", optimize=False)

        compare = make_compare(
            before_preview,
            after_preview,
            f"token {tid:04d} | {it['pattern']} | {it['palette_id']} | {it.get('collar_type')} -> checkered_collar",
        )
        compare.save(out_compare / cmp_name, format="PNG", optimize=False)

        records.append(
            {
                "token_id": tid,
                "pattern": it["pattern"],
                "palette_id": it["palette_id"],
                "rarity_tier": it["rarity_tier"],
                "rarity_type": it["rarity_type"],
                "before_collar_type": it.get("collar_type"),
                "after_collar_type": "checkered_collar",
                "before_24": rel(out_before24 / b24_name),
                "after_24": rel(out_after24 / a24_name),
                "after_preview": rel(out_after_preview / apv_name),
                "compare": rel(out_compare / cmp_name),
            }
        )

    out_manifest = {
        "version": "collar_adjustment_wave1_preview_v1",
        "selected_none_to_checkered": selected.none_to_checkered,
        "selected_classic_to_checkered": selected.classic_to_checkered,
        "count_total": len(all_ids),
        "items": records,
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(out_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_dir / "README.md").write_text(
        "# 30_after_change_preview_7tokens\n\n"
        "- `before_24`: current final state (24x24)\n"
        "- `after_24`: simulated state after collar adjustment (24x24)\n"
        "- `after_preview`: simulated state at preview scale for manifest source replacement\n"
        "- `compare`: enlarged side-by-side preview for visual check\n",
        encoding="utf-8",
    )

    print(f"[preview-collar-adjustment] out_dir={args.out_dir}")
    print(f"[preview-collar-adjustment] tokens={all_ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
