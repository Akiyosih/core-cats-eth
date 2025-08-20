#!/usr/bin/env python3
# coding: utf-8
"""
Core Cats: selected/png の内容を走査し、以下を表示するスクリプト。
1) 模様9種ごとの総枚数
2) 模様ごとのパレット内訳
3) 「ナチュラル」「スペシャル」パレットの集計
   - 模様を問わない全体合計
   - 模様ごとの合計

想定ファイル名: <pattern>__<palette>__<id>.png
例: calico__black_white__000123.png
"""


import os
import re
import argparse
from collections import Counter, defaultdict

# 既定の模様9種（スクリーンショット準拠）
DEFAULT_PATTERNS = [
    "calico",
    "classic_tabby",
    "hachiware",
    "mackerel_tabby",
    "masked",
    "pointed",
    "solid",
    "tortoiseshell",
    "tuxedo",
]

FILENAME_RE = re.compile(r"^([a-z0-9_]+)__([a-z0-9_]+)__(\d+)\.png$", re.IGNORECASE)

NATURAL_PALETTES = {
    "orange_warm",
    "tricolor_soft",
    "black_solid",
    "black_white",
    "gray_soft",
    "orange_white",
    "earth_tone",
    "ivory_brown",
}
SPECIAL_PALETTES = {
    "cyberpunk",
    "psychedelic",
    "tropical_fever",
    "zombie",
    "space_nebula",
}


def parse_args():
    p = argparse.ArgumentParser(description="Core Cats: selected/png の模様・パレット集計")
    p.add_argument(
        "--dir",
        default=r"C:\Users\b8_q6\core-cats-eth\art\selected\png",
        help="走査対象ディレクトリ（省略時は既定パス）",
    )
    p.add_argument(
        "--patterns",
        default=",".join(DEFAULT_PATTERNS),
        help="模様のカンマ区切りリスト（省略時は既定の9種）",
    )
    p.add_argument(
        "--limit-palettes",
        type=int,
        default=None,
        help="各模様のパレット表示を上位N件に制限（省略時は全件）",
    )
    p.add_argument(
        "--show-empty",
        action="store_true",
        help="0枚の模様も表示する",
    )
    return p.parse_args()

def main():
    args = parse_args()
    target_dir = args.dir
    patterns = [s.strip().lower() for s in args.patterns.split(",") if s.strip()]
    pattern_set = set(patterns)

    if not os.path.isdir(target_dir):
        print(f"ERROR: ディレクトリが見つかりません: {target_dir}")
        return

    total_png = 0
    mismatched = 0
    unknown_pattern = 0

    # 模様ごとにパレット頻度を集計
    per_pattern_palette = defaultdict(Counter)
    per_pattern_total = Counter()

    # 追加: 模様ごとのナチュラル／スペシャル合計
    per_pattern_natural_total = Counter()
    per_pattern_special_total = Counter()
    # 追加: 模様を問わない全体のナチュラル／スペシャル合計
    global_natural_total = 0
    global_special_total = 0
    global_unknown_palette = 0

    for name in os.listdir(target_dir):
        path = os.path.join(target_dir, name)
        if not os.path.isfile(path) or not name.lower().endswith(".png"):
            continue

        total_png += 1
        m = FILENAME_RE.match(name)
        if not m:
            mismatched += 1
            continue

        pattern, palette, _id = m.group(1).lower(), m.group(2).lower(), m.group(3)
        if pattern not in pattern_set:
            unknown_pattern += 1
            # 「その他」として集計したい場合は下行のコメントアウトを外す
            # per_pattern_palette["_others_"][palette] += 1
            # per_pattern_total["_others_"] += 1
            continue

        per_pattern_total[pattern] += 1
        per_pattern_palette[pattern][palette] += 1

        # パレット分類カウント
        if palette in NATURAL_PALETTES:
            per_pattern_natural_total[pattern] += 1
            global_natural_total += 1
        elif palette in SPECIAL_PALETTES:
            per_pattern_special_total[pattern] += 1
            global_special_total += 1
        else:
            global_unknown_palette += 1

    # 出力
    print("=== Core Cats 選別PNG 集計 ===")
    print(f"- 走査対象フォルダ: {target_dir}")
    print(f"- 合計ファイル数(.png): {total_png}")
    print(f"- ファイル名形式に不一致: {mismatched}")
    print(f"- 未知パターン件数: {unknown_pattern}")
    print("")

    # 追加: 模様を問わないパレット分類合計
    print("=== ナチュラル／スペシャル合計（模様問わず） ===")
    print(f"- natural_palettes 合計: {global_natural_total}")
    print(f"- special_palettes 合計: {global_special_total}")
    print(f"- 未分類パレット: {global_unknown_palette}")
    print("")


    print("=== 模様ごとの枚数とパレット内訳 ===")
    for pattern in patterns:
        count = per_pattern_total.get(pattern, 0)
        if count == 0 and not args.show_empty:
            continue

        print(f"- {pattern}: {count}")
        if count > 0:

            # 追加: 各模様のナチュラル／スペシャル合計
            nat = per_pattern_natural_total.get(pattern, 0)
            spe = per_pattern_special_total.get(pattern, 0)
            print(f"  - natural合計: {nat}")
            print(f"  - special合計: {spe}")

            items = per_pattern_palette[pattern].most_common()
            if args.limit_palettes is not None:
                items = items[: args.limit_palettes]
            for pal, cnt in items:
                print(f"  - {pal}: {cnt}")
        # 見やすさ用の空行
        print("")

    # 0枚の模様も明示したい場合（--show-empty で既に表示済み）
    if not args.show_empty:
        empty_patterns = [p for p in patterns if per_pattern_total.get(p, 0) == 0]
        if empty_patterns:
            print("- 0枚の模様（省略表示）:", ", ".join(empty_patterns))

if __name__ == "__main__":
    main()
