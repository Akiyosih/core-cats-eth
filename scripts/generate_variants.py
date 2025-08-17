import os
import json
import time
from hashlib import sha256
from pathlib import Path
from itertools import permutations, product
from PIL import Image


def load_palettes(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
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
    return pallets, gconf

def load_patterns(pattern_dir):
    patterns = {}
    for file in os.listdir(pattern_dir):
        if file.endswith(".png"):
            pattern_name = os.path.splitext(file)[0]
            patterns[pattern_name] = Image.open(
                os.path.join(pattern_dir, file)
            ).convert("RGBA")
    return patterns


def extract_slot_colors(img: Image.Image):
    """非透明ピクセルのRGBユニーク色を面積降順に並べる。"""
    img = img.convert("RGBA")
    w, h = img.size
    pix = img.load()
    counts = {}
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            # 背景(完全透明=0)はスロットから除外し、模様(α>0)のみを候補にする
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
            # スロット外(不透明でない画素)は着色対象にしない
            if a != 255:
                continue
            key = (r, g, b)
            if key in mapping:
                nr, ng, nb = mapping[key]
                pix[x, y] = (nr, ng, nb, a)
    return img


def normalize_rgb(img: Image.Image, size=(24, 24), max_colors=16, dither=False) -> Image.Image:
    """
    透過を保持したまま正規化する:
      - RGBAのまま24×24へ最近傍リサイズ
      - RGBのみ減色（αは保持）
      - 返り値も RGBA（背景は透過のまま）
      - 透明画素(α==0)のRGBは(0,0,0)に丸め、ビューア差によるにじみを抑止
    """
    im = img.resize(size, Image.NEAREST).convert("RGBA")
    r, g, b, a = im.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb_q = rgb.quantize(
        colors=max_colors,
        method=Image.Quantize.FASTOCTREE,
        dither=(Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE),
    ).convert("RGB")
    rq, gq, bq = rgb_q.split()
    out = Image.merge("RGBA", (rq, gq, bq, a))
    # 透明画素のRGBを黒に丸める（見た目は変わらないが安全）
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            rr, gg, bb, aa = px[x, y]
            if aa == 0 and (rr or gg or bb):
                px[x, y] = (0, 0, 0, 0)
    return out


def _hex_tuple_to_key(hex_tuple):
    """('#RRGGBB', ...) をユニークキー化（大文字化で正規化）。"""
    return tuple(h.upper() for h in hex_tuple)


def enumerate_color_tuples(k: int, palette_hex: list):
    """
    ルールに基づく全列挙：
      - k == m: パレット色の全順列（k!）
      - k <  m: パレットから重複なし・順序ありで k 色（P(m,k)）
      - k >  m: パレット色の重複使用を許可（m^k）し、単色 m 通りを除外 → m^k - m
                ※ m==1 かつ k>=2 は 0 通り
    戻り値は HEX 文字列タプルの反復子。
    """
    m = len(palette_hex)
    # 安全側の正規化
    palette_hex = [h.upper() for h in palette_hex]
    if m == 0 or k <= 0:
        return []
    if k == m:
        # 全順列
        return permutations(palette_hex, k)
    if k < m:
        # 重複なし・順序あり
        return permutations(palette_hex, k)
    # k > m
    if m == 1:
        # 単色パレットを多スロットへは適用しない（0通り）
        return []
    # 重複許可の全列挙から単色を除外
    def _iter():
        for tup in product(palette_hex, repeat=k):
            # 単色（全要素同一）は除外
            if len(set(tup)) == 1:
                continue
            yield tup
    return _iter()


def generate_variants(pattern_dir, palette_config, out_png_dir, manifest_path):
    Path(out_png_dir).mkdir(parents=True, exist_ok=True)
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    palettes, gconf = load_palettes(palette_config)
    patterns = load_patterns(pattern_dir)
    # 並び順の安定化（決定論）
    patterns = dict(sorted(patterns.items(), key=lambda kv: kv[0]))
    palettes_sorted = sorted(palettes, key=lambda t: (t[0], t[1]))  # (category, palette_id)
    used_keys = set()  # (pattern, color_tuple) のユニーク判定
    total_out = 0
    by_cat = {"natural": 0, "special": 0}
    print(f"[start] patterns={len(patterns)} palettes={len(palettes_sorted)} out_dir={out_png_dir}")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        for pname, pimg in patterns.items():
            slots = extract_slot_colors(pimg)
            k = len(slots)
            variant_idx = 0
            for cat, pal_id, pal_colors in palettes_sorted:
                # 全列挙（ケース別）
                for hex_tuple in enumerate_color_tuples(k, pal_colors):
                    key = (pname, _hex_tuple_to_key(hex_tuple))
                    if key in used_keys:
                        continue
                    used_keys.add(key)
                    recolored = recolor_pattern(pimg, slots, list(hex_tuple))
                    out_img = normalize_rgb(
                        recolored,
                        size=gconf.get("image_size", (24, 24)),
                        max_colors=gconf.get("quantize_colors", 16),
                        dither=gconf.get("dither", False),
                    )
                    out_path = Path(out_png_dir) / f"{pname}__{pal_id}__{variant_idx:06d}.png"
                    out_img.save(out_path, format="PNG", optimize=False)
                    variant_idx += 1
                    total_out += 1
                    by_cat[cat] = by_cat.get(cat, 0) + 1
                    variant_key = sha256(("|".join(_hex_tuple_to_key(hex_tuple))).encode("utf-8")).hexdigest()
                    rec = {
                        "file": str(out_path).replace("\\","/"),
                        "pattern": pname,
                        "slots": k,
                        "category": cat,
                        "palette_id": pal_id,
                        "palette_colors": pal_colors,
                        "color_tuple": list(hex_tuple),
                        "variant_key": variant_key,
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                    mf.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[done]   out={total_out} dist={by_cat} manifest={manifest_path}")


if __name__ == "__main__":
    pattern_dir = "art/parts/patterns"
    palette_config = "art/palettes/pattern_config.json"
    out_png_dir = "art/generated/png"
    manifest_path = "manifests/generated.jsonl"
    generate_variants(pattern_dir, palette_config, out_png_dir, manifest_path)
