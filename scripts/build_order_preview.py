#!/usr/bin/env python3
"""
Build preview-only ordered outputs from final_1000_manifest.

Outputs:
- art/review/order_preview_wave1/ordered_png/*
- art/review/order_preview_wave1/contact_sheets/*.png
- art/review/order_preview_wave1/ordered_manifest.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "final_1000_manifest_v1.json"
DEFAULT_ORDER = ROOT / "manifests" / "order_preview_wave1_20260306.json"
DEFAULT_OUT = ROOT / "art" / "review" / "order_preview_wave1"

THUMB = 128
COLS = 8
PADDING = 16
CAPTION_H = 24
HEADER_H = 44
SECTION_H = 26
BG = (18, 21, 29, 255)
PANEL = (30, 35, 48, 255)
TEXT = (237, 240, 245, 255)
MUTED = (166, 176, 192, 255)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def sort_items(items: list[dict], order_doc: dict) -> list[dict]:
    pattern_order = {name: i for i, name in enumerate(order_doc["pattern_order"])}
    natural_order = {name: i for i, name in enumerate(order_doc["palette_order"]["natural"])}
    special_order = {name: i for i, name in enumerate(order_doc["palette_order"]["special"])}
    category_rank = {"natural": 0, "special": 1, "superrare": 2}
    rarity_rank = {"common": 0, "rare": 1, "superrare": 2}
    superrare_cfg = order_doc.get("superrare", {})
    superrare_order = superrare_cfg.get("order", "token_id")
    if isinstance(superrare_order, list):
        superrare_rank = {name: i for i, name in enumerate(superrare_order)}
    else:
        superrare_rank = {}

    def origin_index(it: dict) -> int:
        origin = str(it.get("base_origin_file_24") or "")
        m = re.search(r"__(\d+)\.png$", origin)
        if not m:
            return 999999
        return int(m.group(1))

    def key(it: dict):
        pattern = str(it["pattern"])
        category = str(it["category"])
        palette = str(it["palette_id"])
        rarity_tier = str(it["rarity_tier"])
        if rarity_tier == "superrare":
            if superrare_rank:
                return (999, 999, 999, superrare_rank.get(str(it["rarity_type"]), 999), int(it["token_id"]))
            return (999, 999, 999, int(it["token_id"]))
        if category == "natural":
            palette_idx = natural_order.get(palette, 999)
        elif category == "special":
            palette_idx = special_order.get(palette, 999)
        else:
            palette_idx = 999
        return (
            pattern_order.get(pattern, 999),
            category_rank.get(category, 999),
            palette_idx,
            origin_index(it),
            rarity_rank.get(rarity_tier, 999),
            1 if bool(it.get("collar")) else 0,
            int(it["token_id"]),
        )

    return sorted(items, key=key)


def build_ordered_manifest(sorted_items: list[dict], order_doc: dict) -> dict:
    return {
        "version": "order_preview_wave1_manifest_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_manifest": rel(DEFAULT_MANIFEST),
        "order_spec": rel(DEFAULT_ORDER),
        "total": len(sorted_items),
        "items": [
            {
                "order_index": i + 1,
                "token_id": int(it["token_id"]),
                "pattern": str(it["pattern"]),
                "category": str(it["category"]),
                "palette_id": str(it["palette_id"]),
                "rarity_tier": str(it["rarity_tier"]),
                "rarity_type": str(it["rarity_type"]),
                "review_file": str(it["review_file"]),
            }
            for i, it in enumerate(sorted_items)
        ],
    }


def copy_ordered_pngs(sorted_items: list[dict], ordered_dir: Path) -> None:
    if ordered_dir.exists():
        for p in ordered_dir.glob("*.png"):
            p.unlink()
    ordered_dir.mkdir(parents=True, exist_ok=True)

    for i, it in enumerate(sorted_items, start=1):
        src = ROOT / str(it["review_file"])
        rarity = str(it["rarity_tier"])
        name = (
            f"{i:04d}__token_{int(it['token_id']):04d}__"
            f"{it['pattern']}__{it['category']}__{it['palette_id']}__{rarity}.png"
        )
        shutil.copy2(src, ordered_dir / name)


def load_font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def fit_thumb(src: Path) -> Image.Image:
    img = Image.open(src).convert("RGBA")
    return img.resize((THUMB, THUMB), Image.NEAREST)


def build_pattern_sheet(pattern: str, items: list[dict], out_path: Path) -> None:
    font_title = load_font(22)
    font_body = load_font(14)

    natural = [it for it in items if it["category"] == "natural"]
    special = [it for it in items if it["category"] == "special"]
    sections = []
    if natural:
        sections.append(("Natural", natural))
    if special:
        sections.append(("Special", special))
    if not sections:
        sections.append(("Other", items))

    rows_total = 0
    for _, sec_items in sections:
        rows_total += math.ceil(len(sec_items) / COLS)

    width = PADDING * 2 + COLS * THUMB + (COLS - 1) * 8
    height = PADDING * 2 + HEADER_H + len(sections) * SECTION_H + rows_total * (THUMB + CAPTION_H + 8) + 24
    canvas = Image.new("RGBA", (width, height), BG)
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((8, 8, width - 8, height - 8), 18, fill=PANEL)
    draw.text((PADDING, PADDING), f"{pattern} ({len(items)})", fill=TEXT, font=font_title)

    y = PADDING + HEADER_H
    for section_name, sec_items in sections:
        draw.text((PADDING, y), section_name, fill=MUTED, font=font_body)
        y += SECTION_H
        for idx, it in enumerate(sec_items):
            row = idx // COLS
            col = idx % COLS
            x = PADDING + col * (THUMB + 8)
            yy = y + row * (THUMB + CAPTION_H + 8)
            thumb = fit_thumb(ROOT / str(it["review_file"]))
            canvas.alpha_composite(thumb, (x, yy))
            caption = f"{int(it['token_id']):04d} {it['palette_id']}"
            draw.text((x, yy + THUMB + 4), caption, fill=TEXT, font=font_body)
        y += math.ceil(len(sec_items) / COLS) * (THUMB + CAPTION_H + 8)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG", optimize=False)


def build_master_pages(sorted_items: list[dict], out_dir: Path) -> None:
    font_title = load_font(18)
    font_body = load_font(12)
    per_page = 40
    cols = 5
    thumb = 144
    caption_h = 22
    gap = 12
    for old in out_dir.glob("page_*.png"):
        old.unlink()

    total_pages = math.ceil(len(sorted_items) / per_page)
    for page in range(total_pages):
        chunk = sorted_items[page * per_page : (page + 1) * per_page]
        rows = math.ceil(len(chunk) / cols)
        width = PADDING * 2 + cols * thumb + (cols - 1) * gap
        height = PADDING * 2 + HEADER_H + rows * (thumb + caption_h + gap)
        canvas = Image.new("RGBA", (width, height), BG)
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((8, 8, width - 8, height - 8), 18, fill=PANEL)
        draw.text((PADDING, PADDING), f"Order Preview page {page + 1}/{total_pages}", fill=TEXT, font=font_title)
        y0 = PADDING + HEADER_H
        for idx, it in enumerate(chunk):
            row = idx // cols
            col = idx % cols
            x = PADDING + col * (thumb + gap)
            y = y0 + row * (thumb + caption_h + gap)
            thumb_img = Image.open(ROOT / str(it["review_file"])).convert("RGBA").resize((thumb, thumb), Image.NEAREST)
            canvas.alpha_composite(thumb_img, (x, y))
            label = f"{page * per_page + idx + 1:04d} -> {int(it['token_id']):04d}"
            draw.text((x, y + thumb + 4), label, fill=TEXT, font=font_body)
        canvas.save(out_dir / f"page_{page + 1:02d}.png", format="PNG", optimize=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build order preview outputs.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--order", type=Path, default=DEFAULT_ORDER)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    order_doc = load_json(args.order)
    items = manifest["items"]
    sorted_items = sort_items(items, order_doc)

    out_root = args.out
    ordered_dir = out_root / "ordered_png"
    sheets_dir = out_root / "contact_sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)

    copy_ordered_pngs(sorted_items, ordered_dir)
    write_json(out_root / "ordered_manifest.json", build_ordered_manifest(sorted_items, order_doc))

    grouped: dict[str, list[dict]] = defaultdict(list)
    for it in sorted_items:
        grouped[str(it["pattern"])].append(it)

    for idx, pattern in enumerate(order_doc["pattern_order"], start=1):
        if pattern in grouped:
            build_pattern_sheet(pattern, grouped[pattern], sheets_dir / f"{idx:02d}__{pattern}.png")
    if "superrare" in grouped:
        build_pattern_sheet("superrare", grouped["superrare"], sheets_dir / "99__superrare.png")

    build_master_pages(sorted_items, sheets_dir)

    print(f"[order-preview] out={out_root}")
    print(f"[order-preview] ordered_png={ordered_dir}")
    print(f"[order-preview] contact_sheets={sheets_dir}")
    print(f"[order-preview] total={len(sorted_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
