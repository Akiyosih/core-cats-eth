#!/usr/bin/env python3
# scripts/verify_alpha_binary.py
#
# 使い方（PowerShellの例）:
#   python .\scripts\verify_alpha_binary.py C:\Users\b8_q6\core-cats-eth\art\parts\patterns
#
# 機能:
#  - 引数のパス以下を再帰探索し *.png を対象に検査
#  - αが {0,255} 以外の画素が1つでもあれば NG として報告
#  - 終了コード: OK=0, NG=1, エラー=2

import sys
import pathlib
from PIL import Image

def check_png_alpha_binary(path: pathlib.Path, max_report_px=10):
    """
    画像1枚を検査。戻り値: (is_ok: bool, first_bad_pixels: [(x,y,a), ...])
    """
    try:
        im = Image.open(path).convert("RGBA")
    except Exception as e:
        return False, [("open_error", str(e), -1)]
    w, h = im.size
    px = im.load()
    bad = []
    for y in range(h):
        for x in range(w):
            _, _, _, a = px[x, y]
            if a not in (0, 255):
                bad.append((x, y, a))
                if len(bad) >= max_report_px:
                    return False, bad
    return True, bad  # bad は空配列のはず

def main():
    if len(sys.argv) < 2:
        print("使い方: python scripts/verify_alpha_binary.py <dir_or_png>")
        sys.exit(2)

    target = pathlib.Path(sys.argv[1])
    if not target.exists():
        print(f"パスが存在しません: {target}")
        sys.exit(2)

    # 対象一覧を作成
    pngs = []
    if target.is_file() and target.suffix.lower() == ".png":
        pngs = [target]
    else:
        pngs = list(target.rglob("*.png"))

    if not pngs:
        print("PNGが見つかりません。")
        sys.exit(2)

    total = 0
    ng_files = []
    for p in sorted(pngs):
        total += 1
        ok, info = check_png_alpha_binary(p)
        if not ok:
            ng_files.append((p, info))

    if not ng_files:
        print(f"[alpha-binary] OK: {total} files checked, no semi-transparent pixels found.")
        sys.exit(0)

    print(f"[alpha-binary] NG: {len(ng_files)} / {total} files に 0/255 以外のαが見つかりました。")
    for p, bad in ng_files[:20]:  # 多すぎる場合は先頭20件だけ列挙
        print(f"  - {p}")
        for (x, y, a) in bad:
            if x == 'open_error':
                print(f"      * open_error: {y}")
            else:
                print(f"      * (x={x}, y={y}, a={a})")
    if len(ng_files) > 20:
        print("  ... (省略)")

    sys.exit(1)

if __name__ == "__main__":
    main()
