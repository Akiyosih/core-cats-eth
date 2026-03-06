#!/usr/bin/env python3
"""
Generate compact Solidity constants from final_1000_manifest and 24x24 PNG assets.

Output:
- contracts/CoreCatsOnchainData.sol
"""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "final_1000_manifest_v1.json"
DEFAULT_OUT = ROOT / "contracts" / "CoreCatsOnchainData.sol"
ART_ROOT = ROOT / "art"

PATTERN_NAMES = [
    "solid",
    "socks",
    "pointed",
    "patched",
    "hachiware",
    "tuxedo",
    "masked",
    "classic_tabby",
    "mackerel_tabby",
    "tortoiseshell",
    "superrare",
]

PATTERN_SOURCE_FILES = {
    "solid": "solid.png",
    "socks": "calico.png",
    "pointed": "pointed.png",
    "patched": "calico.png",
    "hachiware": "hachiware.png",
    "tuxedo": "tuxedo.png",
    "masked": "masked.png",
    "classic_tabby": "classic_tabby.png",
    "mackerel_tabby": "mackerel_tabby.png",
    "tortoiseshell": "tortoiseshell.png",
}

PALETTE_NAMES = [
    "black_white",
    "cyberpunk",
    "earth_tone",
    "gray_soft",
    "orange_warm",
    "orange_white",
    "psychedelic",
    "space_nebula",
    "tricolor_soft",
    "tropical_fever",
    "zombie",
    "ivory_brown",
    "black_solid",
    "superrare",
]

COLLAR_TYPE_NAMES = ["none", "checkered_collar", "classic_red_collar"]
RARITY_TIER_NAMES = ["common", "rare", "superrare"]
RARITY_TYPE_NAMES = [
    "none",
    "odd_eyes",
    "red_nose",
    "blue_nose",
    "glasses",
    "sunglasses",
    "corelogo",
    "pinglogo",
]

# Order used by renderer.
FIXED_LAYER_FILES = [
    "art/base/base.png",  # 0
    "art/parts/accessories/collar/checkered_collar.png",  # 1
    "art/parts/accessories/collar/classic_red_collar.png",  # 2
    "art/parts/rare/odd_eyes.png",  # 3
    "art/parts/rare/red_nose.png",  # 4
    "art/parts/rare/blue_nose.png",  # 5
    "art/parts/rare/glasses.png",  # 6
    "art/parts/rare/sunglasses.png",  # 7
    "art/tmp/Core1.png",  # 8
    "art/tmp/Ping1.png",  # 9
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Solidity on-chain data constants.")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def parse_png_rgba(path: Path) -> list[list[tuple[int, int, int, int]]]:
    b = path.read_bytes()
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Invalid PNG signature: {path}")

    i = 8
    width = height = None
    idat_parts: list[bytes] = []

    while i < len(b):
        if i + 12 > len(b):
            raise RuntimeError(f"Corrupt PNG chunk header: {path}")
        length = struct.unpack(">I", b[i : i + 4])[0]
        i += 4
        ctype = b[i : i + 4]
        i += 4
        data = b[i : i + length]
        i += length
        i += 4  # CRC

        if ctype == b"IHDR":
            width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", data)
            if (bit_depth, color_type, comp, filt, interlace) != (8, 6, 0, 0, 0):
                raise RuntimeError(
                    f"Unsupported PNG format in {path}: bit_depth={bit_depth}, color_type={color_type}, "
                    f"comp={comp}, filter={filt}, interlace={interlace}"
                )
        elif ctype == b"IDAT":
            idat_parts.append(data)
        elif ctype == b"IEND":
            break

    if width != 24 or height != 24:
        raise RuntimeError(f"Expected 24x24 PNG, got {width}x{height}: {path}")

    raw = zlib.decompress(b"".join(idat_parts))
    stride = width * 4

    out: list[list[tuple[int, int, int, int]]] = [[(0, 0, 0, 0)] * width for _ in range(height)]
    prev = bytearray(stride)
    ptr = 0

    def paeth(a: int, b_: int, c: int) -> int:
        p = a + b_ - c
        pa = abs(p - a)
        pb = abs(p - b_)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b_
        return c

    for y in range(height):
        filt = raw[ptr]
        ptr += 1
        row = bytearray(raw[ptr : ptr + stride])
        ptr += stride

        if filt == 0:
            pass
        elif filt == 1:
            for x in range(stride):
                row[x] = (row[x] + (row[x - 4] if x >= 4 else 0)) & 0xFF
        elif filt == 2:
            for x in range(stride):
                row[x] = (row[x] + prev[x]) & 0xFF
        elif filt == 3:
            for x in range(stride):
                left = row[x - 4] if x >= 4 else 0
                up = prev[x]
                row[x] = (row[x] + ((left + up) // 2)) & 0xFF
        elif filt == 4:
            for x in range(stride):
                left = row[x - 4] if x >= 4 else 0
                up = prev[x]
                up_left = prev[x - 4] if x >= 4 else 0
                row[x] = (row[x] + paeth(left, up, up_left)) & 0xFF
        else:
            raise RuntimeError(f"Unsupported PNG filter={filt} in {path}")

        prev = row
        for x in range(width):
            i4 = x * 4
            out[y][x] = (row[i4], row[i4 + 1], row[i4 + 2], row[i4 + 3])

    return out


def pack_nibbles(values: Iterable[int]) -> bytes:
    vals = list(values)
    if len(vals) % 2 != 0:
        raise RuntimeError("Nibble source must have even length")
    out = bytearray()
    for i in range(0, len(vals), 2):
        a = vals[i]
        b = vals[i + 1]
        if not (0 <= a <= 15 and 0 <= b <= 15):
            raise RuntimeError(f"Nibble out of range: {a}, {b}")
        out.append((a << 4) | b)
    return bytes(out)


def to_hex(data: bytes) -> str:
    return data.hex()


def build_pattern_data() -> tuple[bytes, bytes]:
    slot_counts: list[int] = []
    packed_all = bytearray()

    for name in PATTERN_NAMES[:-1]:  # exclude synthetic "superrare"
        source_name = PATTERN_SOURCE_FILES[name]
        path = ART_ROOT / "parts" / "patterns" / source_name
        px = parse_png_rgba(path)
        counts: Counter[tuple[int, int, int]] = Counter()
        for row in px:
            for r, g, b, a in row:
                if a > 0:
                    counts[(r, g, b)] += 1

        # Must match generation logic in scripts/generate_variants.py (area-desc order)
        slot_colors = [rgb for rgb, _ in counts.most_common()]
        slot_count = len(slot_colors)
        if not (1 <= slot_count <= 4):
            raise RuntimeError(f"Unexpected slot count={slot_count} in {path}")

        color_to_idx = {rgb: i + 1 for i, rgb in enumerate(slot_colors)}
        nibs: list[int] = []
        for row in px:
            for r, g, b, a in row:
                if a == 0:
                    nibs.append(0)
                else:
                    nibs.append(color_to_idx[(r, g, b)])

        packed = pack_nibbles(nibs)
        if len(packed) != 288:
            raise RuntimeError(f"Pattern packed size must be 288 bytes, got {len(packed)} in {path}")

        slot_counts.append(slot_count)
        packed_all.extend(packed)

    # append synthetic superrare entry (no slots, no mask)
    slot_counts.append(0)

    if len(slot_counts) != len(PATTERN_NAMES):
        raise RuntimeError("pattern slot count table size mismatch")

    return bytes(slot_counts), bytes(packed_all)


def build_fixed_layer_data() -> tuple[bytes, bytes, bytes]:
    packed_pixels = bytearray()
    palette_meta = bytearray()  # 3 bytes per layer: offset_hi, offset_lo, count
    palette_bytes = bytearray()

    for rel in FIXED_LAYER_FILES:
        path = ROOT / rel
        px = parse_png_rgba(path)

        color_to_idx: dict[tuple[int, int, int], int] = {}
        palette_list: list[tuple[int, int, int]] = []
        nibs: list[int] = []

        for row in px:
            for r, g, b, a in row:
                if a == 0:
                    nibs.append(0)
                    continue
                key = (r, g, b)
                if key not in color_to_idx:
                    if len(palette_list) >= 15:
                        raise RuntimeError(f"Too many colors in {path}")
                    palette_list.append(key)
                    color_to_idx[key] = len(palette_list)  # 1..15
                nibs.append(color_to_idx[key])

        packed = pack_nibbles(nibs)
        if len(packed) != 288:
            raise RuntimeError(f"Fixed layer packed size must be 288 bytes, got {len(packed)} in {path}")

        offset = len(palette_bytes) // 3
        count = len(palette_list)
        if offset > 65535:
            raise RuntimeError("Palette offset overflow")
        palette_meta.extend(bytes([(offset >> 8) & 0xFF, offset & 0xFF, count]))
        for r, g, b in palette_list:
            palette_bytes.extend(bytes([r, g, b]))

        packed_pixels.extend(packed)

    return bytes(packed_pixels), bytes(palette_meta), bytes(palette_bytes)


def hex_color_to_rgb(h: str) -> tuple[int, int, int]:
    s = h.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) != 6:
        raise RuntimeError(f"Invalid color: {h}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def build_tuple_and_token_records(manifest: dict) -> tuple[bytes, bytes, bytes]:
    pattern_map = {n: i for i, n in enumerate(PATTERN_NAMES)}
    palette_map = {n: i for i, n in enumerate(PALETTE_NAMES)}
    collar_map = {n: i for i, n in enumerate(COLLAR_TYPE_NAMES)}
    tier_map = {n: i for i, n in enumerate(RARITY_TIER_NAMES)}
    rtype_map = {n: i for i, n in enumerate(RARITY_TYPE_NAMES)}

    items = sorted(manifest["items"], key=lambda x: int(x["token_id"]))
    if len(items) != 1000:
        raise RuntimeError(f"Expected 1000 items, got {len(items)}")

    tuple_to_index: dict[tuple[str, ...], int] = {tuple(): 0}
    tuples: list[tuple[str, ...]] = [tuple()]

    records = bytearray()

    for i, item in enumerate(items, start=1):
        tid = int(item["token_id"])
        if tid != i:
            raise RuntimeError(f"token_id sequence mismatch at index={i}, got token_id={tid}")

        color_tuple = tuple(item.get("color_tuple") or [])
        if color_tuple not in tuple_to_index:
            tuple_to_index[color_tuple] = len(tuples)
            tuples.append(color_tuple)
        tuple_idx = tuple_to_index[color_tuple]

        pattern_id = pattern_map[item["pattern"]]
        palette_id = palette_map[item["palette_id"]]
        collar_id = collar_map[item["collar_type"]]
        tier_id = tier_map[item["rarity_tier"]]
        rtype_id = rtype_map[item["rarity_type"]]

        packed = (
            (pattern_id & 0xF)
            | ((palette_id & 0xF) << 4)
            | ((collar_id & 0x3) << 8)
            | ((tier_id & 0x3) << 10)
            | ((rtype_id & 0xF) << 12)
            | ((tuple_idx & 0x1FF) << 16)
        )
        records.extend(bytes([packed & 0xFF, (packed >> 8) & 0xFF, (packed >> 16) & 0xFF, (packed >> 24) & 0xFF]))

    if len(records) != 4000:
        raise RuntimeError(f"Unexpected token record length: {len(records)}")

    tuple_meta = bytearray()  # 3 bytes/tuple: color_offset_hi, color_offset_lo, len
    tuple_colors = bytearray()  # RGB triples

    color_offset = 0
    for tup in tuples:
        if color_offset > 65535:
            raise RuntimeError("tuple color offset overflow")
        if len(tup) > 4:
            raise RuntimeError(f"tuple length overflow: {tup}")

        tuple_meta.extend(bytes([(color_offset >> 8) & 0xFF, color_offset & 0xFF, len(tup)]))
        for h in tup:
            r, g, b = hex_color_to_rgb(h)
            tuple_colors.extend(bytes([r, g, b]))
        color_offset += len(tup)

    return bytes(records), bytes(tuple_meta), bytes(tuple_colors)


def build_solidity(
    token_records: bytes,
    tuple_meta: bytes,
    tuple_colors: bytes,
    pattern_slot_counts: bytes,
    pattern_masks: bytes,
    fixed_layer_pixels: bytes,
    fixed_layer_palette_meta: bytes,
    fixed_layer_palettes: bytes,
) -> str:
    return f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @notice Auto-generated by scripts/generate_onchain_data.py. Do not edit manually.
contract CoreCatsOnchainData {{
    uint256 public constant TOKEN_COUNT = 1000;
    uint256 public constant PATTERN_COUNT = {len(PATTERN_NAMES)};
    uint256 public constant FIXED_LAYER_COUNT = {len(FIXED_LAYER_FILES)};

    // Packed uint32 per token (little-endian):
    // bits 0..3   pattern_id
    // bits 4..7   palette_id
    // bits 8..9   collar_type_id
    // bits 10..11 rarity_tier_id
    // bits 12..15 rarity_type_id
    // bits 16..24 color_tuple_index (9 bits)
    bytes internal constant TOKEN_RECORDS = hex"{to_hex(token_records)}";

    // 3 bytes per tuple: offset_hi, offset_lo, length
    bytes internal constant COLOR_TUPLE_META = hex"{to_hex(tuple_meta)}";
    // RGB triples, indexed by COLOR_TUPLE_META offset
    bytes internal constant COLOR_TUPLE_COLORS = hex"{to_hex(tuple_colors)}";

    // 1 byte per pattern id (including synthetic superrare=0 slots)
    bytes internal constant PATTERN_SLOT_COUNTS = hex"{to_hex(pattern_slot_counts)}";
    // Nibble-packed 24x24 maps for all non-superrare patterns, 288 bytes each.
    // Value: 0=transparent, 1..4=slot index
    bytes internal constant PATTERN_MASKS = hex"{to_hex(pattern_masks)}";

    // Nibble-packed 24x24 maps, 288 bytes each.
    // Value: 0=transparent, 1..15=palette index
    bytes internal constant FIXED_LAYER_PIXELS = hex"{to_hex(fixed_layer_pixels)}";
    // 3 bytes per layer: palette_offset_hi, palette_offset_lo, palette_count
    bytes internal constant FIXED_LAYER_PALETTE_META = hex"{to_hex(fixed_layer_palette_meta)}";
    // RGB triples for fixed-layer palettes
    bytes internal constant FIXED_LAYER_PALETTES = hex"{to_hex(fixed_layer_palettes)}";

    function tokenRecords() external pure returns (bytes memory) {{
        return TOKEN_RECORDS;
    }}

    function colorTupleMeta() external pure returns (bytes memory) {{
        return COLOR_TUPLE_META;
    }}

    function colorTupleColors() external pure returns (bytes memory) {{
        return COLOR_TUPLE_COLORS;
    }}

    function patternSlotCounts() external pure returns (bytes memory) {{
        return PATTERN_SLOT_COUNTS;
    }}

    function patternMasks() external pure returns (bytes memory) {{
        return PATTERN_MASKS;
    }}

    function fixedLayerPixels() external pure returns (bytes memory) {{
        return FIXED_LAYER_PIXELS;
    }}

    function fixedLayerPaletteMeta() external pure returns (bytes memory) {{
        return FIXED_LAYER_PALETTE_META;
    }}

    function fixedLayerPalettes() external pure returns (bytes memory) {{
        return FIXED_LAYER_PALETTES;
    }}
}}
'''


def main() -> int:
    args = parse_args()

    if not args.manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {args.manifest}")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    pattern_slot_counts, pattern_masks = build_pattern_data()
    fixed_pixels, fixed_meta, fixed_palettes = build_fixed_layer_data()
    token_records, tuple_meta, tuple_colors = build_tuple_and_token_records(manifest)

    out_sol = build_solidity(
        token_records=token_records,
        tuple_meta=tuple_meta,
        tuple_colors=tuple_colors,
        pattern_slot_counts=pattern_slot_counts,
        pattern_masks=pattern_masks,
        fixed_layer_pixels=fixed_pixels,
        fixed_layer_palette_meta=fixed_meta,
        fixed_layer_palettes=fixed_palettes,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out_sol, encoding="utf-8")

    print(f"[onchain-data] out={args.out}")
    print(f"  token_records={len(token_records)} bytes")
    print(f"  tuple_meta={len(tuple_meta)} bytes, tuple_colors={len(tuple_colors)} bytes")
    print(f"  pattern_slot_counts={len(pattern_slot_counts)} bytes, pattern_masks={len(pattern_masks)} bytes")
    print(f"  fixed_layer_pixels={len(fixed_pixels)} bytes")
    print(f"  fixed_layer_palette_meta={len(fixed_meta)} bytes, fixed_layer_palettes={len(fixed_palettes)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
