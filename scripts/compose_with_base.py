#!/usr/bin/env python3
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE_IMG = ROOT / "art" / "base" / "base.PNG"
MANIFEST = ROOT / "manifests" / "generated.jsonl"
PATTERN_DIR = ROOT / "art" / "parts" / "patterns"
PALETTE_CFG = ROOT / "art" / "palettes" / "pattern_config.json"
OUT_DIR = ROOT / "art" / "preview" / "png"

def load_palette_map(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    mp = {}
    for key in ("natural_palettes", "special_palettes"):
        for p in cfg.get(key, []):
            pid = p.get("id") or p.get("name")
            mp[pid] = p.get("colors", [])
    return mp

def extract_slot_colors_rgba(img: Image.Image):
    """非透明ピクセルのRGBユニーク色を面積降順に返す"""
    img = img.convert("RGBA")
    w, h = img.size
    pix = img.load()
    counts = {}
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if a == 0:
                continue
            counts[(r, g, b)] = counts.get((r, g, b), 0) + 1
    ordered = [rgb for rgb, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)]
    return ordered

def recolor_with_palette(src_rgba: Image.Image, base_colors: list, hex_colors: list) -> Image.Image:
    """base_colors [(r,g,b)...] を hex_colors ['#RRGGBB'...] へ順対応で置換（α保持）"""
    img = src_rgba.copy().convert("RGBA")
    pix = img.load()
    w, h = img.size
    to_rgb = []
    for hc in hex_colors:
        hc = hc.lstrip("#")
        to_rgb.append((int(hc[0:2],16), int(hc[2:4],16), int(hc[4:6],16)))
    mapping = {}
    for i, src_rgb in enumerate(base_colors):
        if i < len(to_rgb):
            mapping[src_rgb] = to_rgb[i]
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if a == 0:
                continue
            key = (r, g, b)
            if key in mapping:
                nr, ng, nb = mapping[key]
                pix[x, y] = (nr, ng, nb, a)
    return img

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = Image.open(BASE_IMG).convert("RGBA")
    pmap = load_palette_map(PALETTE_CFG)
    written = 0
    with open(MANIFEST, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            pattern = rec["pattern"]
            pal_id = rec.get("palette_id")
            fname = Path(rec["file"]).name  # 例: cow__cow_bw__000000.png
            src_path = PATTERN_DIR / f"{pattern}.png"
            if not src_path.exists():
                continue
            # 1) まず manifest の color_tuple（実際に使った並び）を最優先
            colors = rec.get("color_tuple")
            # 2) 無い場合のみ、palette_id -> palettes からの定義 or manifest の palette_colors をフォールバック
            if not colors:
                colors = pmap.get(pal_id, rec.get("palette_colors", []))
            if not colors:
                continue
            src = Image.open(src_path).convert("RGBA")
            slots = extract_slot_colors_rgba(src)
            if len(slots) != len(colors):
                continue
            recolored = recolor_with_palette(src, slots, colors)   # α保持
            canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
            canvas.alpha_composite(recolored)  # 模様を先に
            canvas.alpha_composite(base)       # 輪郭を上に
            out_path = OUT_DIR / fname
            canvas.save(out_path, format="PNG", optimize=False)
            written += 1
    print(f"[compose] wrote={written} -> {OUT_DIR}")

if __name__ == "__main__":
    main()