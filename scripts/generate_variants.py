import os
import json
import random
import time
from hashlib import sha256
from pathlib import Path
from PIL import Image


def load_palettes(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    weights = cfg.get("weights", {"natural": 1.0, "special": 0.0})
    pallets = []
    for category_key in ("natural_palettes", "special_palettes"):
        plist = cfg.get(category_key, [])
        category = "natural" if category_key.startswith("natural") else "special"
        for p in plist:
            pid = p.get("id") or p.get("name")
            colors = p.get("colors", [])
            pallets.append((category, pid, colors))
    g = cfg.get("global", {})
    gconf = {
        "image_size": tuple(g.get("image_size", (24, 24))),
        "quantize_colors": int(g.get("quantize_colors", 16)),
        "dither": bool(g.get("dither", False)),
    }
    return weights, pallets, gconf

def load_patterns(pattern_dir):
    patterns = {}
    for file in os.listdir(pattern_dir):
        if file.endswith(".png"):
            pattern_name = os.path.splitext(file)[0]
            patterns[pattern_name] = Image.open(
                os.path.join(pattern_dir, file)
            ).convert("RGBA")
    return patterns


def rng_from_seed(seed_text: str) -> random.Random:
    h = sha256(seed_text.encode("utf-8")).hexdigest()
    return random.Random(int(h, 16) % (2**32))


def choose_category(rng: random.Random, weights: dict) -> str:
    w_nat = float(weights.get("natural", 1.0))
    w_spc = float(weights.get("special", 0.0))
    t = w_nat / (w_nat + w_spc) if (w_nat + w_spc) > 0 else 1.0
    return "natural" if rng.random() < t else "special"


def extract_slot_colors(img: Image.Image):
    """非透明ピクセルのRGBユニーク色を面積降順に並べる。"""
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


def recolor_pattern(pattern_img, base_colors, new_hex_colors):
    """base_colors: [(r,g,b), ...] に対し new_hex_colors: ['#RRGGBB', ...] を順番対応で置換"""
    img = pattern_img.copy().convert("RGBA")
    pix = img.load()
    w, h = img.size
    new_rgb = []
    for hc in new_hex_colors:
        hc = hc.lstrip("#")
        new_rgb.append((int(hc[0:2],16), int(hc[2:4],16), int(hc[4:6],16)))
    mapping = {}
    for i, src_rgb in enumerate(base_colors):
        if i < len(new_rgb):
            mapping[src_rgb] = new_rgb[i]
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


def normalize_rgb(img: Image.Image, size=(24, 24), max_colors=16, dither=False) -> Image.Image:
    base = img.resize(size, Image.NEAREST).convert("RGB")
    base = base.quantize(
        colors=max_colors,
        method=Image.Quantize.FASTOCTREE,
        dither=(Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE),
    )
    return base.convert("RGB")


def generate_variants(pattern_dir, palette_config, out_png_dir, manifest_path, num_variants=320, seed_base="corecats-art-v1"):
    Path(out_png_dir).mkdir(parents=True, exist_ok=True)
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    weights, palettes, gconf = load_palettes(palette_config)
    patterns = load_patterns(pattern_dir)
    with open(manifest_path, "w", encoding="utf-8") as mf:
        for pname, pimg in patterns.items():
            for i in range(num_variants):
                rng = rng_from_seed(f"{seed_base}:{pname}:{i}")
                cat = choose_category(rng, weights)
                pool = [p for p in palettes if p[0] == cat]
                slots = extract_slot_colors(pimg)
                cand = [p for p in pool if len(p[2]) == len(slots)]
                if not cand:
                    other = "natural" if cat == "special" else "special"
                    pool2 = [p for p in palettes if p[0] == other and len(p[2]) == len(slots)]
                    if not pool2:
                        continue
                    choice = rng.choice(pool2)
                else:
                    choice = rng.choice(cand)
                _, pal_id, pal_colors = choice
                recolored = recolor_pattern(pimg, slots, pal_colors)
                out_img = normalize_rgb(
                    recolored,
                    size=gconf.get("image_size", (24, 24)),
                    max_colors=gconf.get("quantize_colors", 16),
                    dither=gconf.get("dither", False),
                )
                out_path = Path(out_png_dir) / f"{pname}__{pal_id}__{i:06d}.png"
                out_img.save(out_path, format="PNG", optimize=False)
                rec = {
                    "file": str(out_path).replace("\\","/"),
                    "pattern": pname,
                    "slots": len(slots),
                    "category": cat,
                    "palette_id": pal_id,
                    "palette_colors": pal_colors,
                    "seed": f"{seed_base}:{pname}:{i}",
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                mf.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    pattern_dir = "art/parts/patterns"
    palette_config = "art/palettes/pattern_config.json"
    out_png_dir = "art/generated/png"
    manifest_path = "manifests/generated.jsonl"
    num = int(os.environ.get("COUNT", "320"))
    seed_base = os.environ.get("SEED_BASE", "corecats-art-v1")
    generate_variants(pattern_dir, palette_config, out_png_dir, manifest_path, num_variants=num, seed_base=seed_base)
