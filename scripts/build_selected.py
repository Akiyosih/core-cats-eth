"""
選別済みPNG(art/selected/png/*.png)のファイル名を、生成時の manifests/generated.jsonl と突き合わせ、
manifests/selected.json を作成する補助スクリプト。

出力(selected.json)には、pattern / palette_id / color_tuple / variant_key など再現に必要な情報を保持する。
"""
import json
import hashlib
from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTED_DIR = ROOT / "art" / "selected" / "png"
DEFAULT_MANIFEST = ROOT / "manifests" / "generated.jsonl"
DEFAULT_OUTJSON = ROOT / "manifests" / "selected.json"
PALETTE_CFG = ROOT / "art" / "palettes" / "pattern_config.json"

def file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as rf:
        for chunk in iter(lambda: rf.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def config_hash(path: Path) -> str:
    if not path.exists():
        return ""
    # JSONとして正規化してからハッシュ化（改行・空白差による揺れを避ける）
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        normalized = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256_bytes(normalized)
    except Exception:
        return sha256_bytes(path.read_bytes())

def load_manifest(manifest_path: Path) -> dict:
    """
    generated.jsonl を読み込み、{ base_filename -> record } の辞書を返す。
    base_filename は 'pattern__palette__000123.png' のようなファイル名のみ。
    """
    m = {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            fname = Path(rec.get("file","")).name
            if not fname:
                continue
            if fname in m:
                # 万一の重複は後勝ちにせず警告したい場合はここで例外化してもよい
                pass
            m[fname] = rec
    return m

def build_selected(selected_dir: Path, manifest_path: Path, out_json: Path) -> int:
    if not manifest_path.exists():
        print(f"manifest が見つかりません: {manifest_path}")
        return 0
    manifest_map = load_manifest(manifest_path)
    items = []
    missing = []
    for png in sorted(selected_dir.glob("*.png")):
        fname = png.name
        rec = manifest_map.get(fname)
        if not rec:
            missing.append(fname)
            continue
        # 再現に必要な最小限のフィールドを抽出
        items.append({
            "file": str(png).replace("\\","/"),
            "filename": fname,
            "pattern": rec.get("pattern"),
            "palette_id": rec.get("palette_id"),
            "color_tuple": rec.get("color_tuple"),
            "variant_key": rec.get("variant_key"),
            "slots": rec.get("slots"),
            "category": rec.get("category"),
            "origin_file": rec.get("file"),
        })
    out = {
        "generated_manifest": str(manifest_path).replace("\\","/"),
        "manifest_hash": file_sha256(manifest_path),
        "palette_config_hash": config_hash(PALETTE_CFG),
        "count": len(items),
        "missing": missing,  # manifest未一致ファイルがあれば確認用に出力
        "items": items
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[selected] wrote={len(items)} missing={len(missing)} -> {out_json}")
    if missing:
        print("  (警告) manifestに見つからなかったファイル名:", ", ".join(missing[:10]), "...")
    return len(items)

def main():
    sel_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SELECTED_DIR
    man_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MANIFEST
    if len(sys.argv) > 3:
        out_path = Path(sys.argv[3])
    else:
        # 自動命名: manifests/selected_wave{N}_{YYYYMMDD_HHMMSS}.json
        manifests_dir = ROOT / "manifests"
        manifests_dir.mkdir(parents=True, exist_ok=True)
        nowstamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 既存の selected_wave*.json を検出して最大Nを求める
        existing = []
        for p in manifests_dir.glob("selected_wave*_*.json"):
            name = p.stem  # e.g., selected_wave3_20250819
            try:
                prefix, rest = name.split("wave", 1)
                n_part = ""
                for ch in rest:
                    if ch.isdigit():
                        n_part += ch
                    else:
                        break
                if n_part:
                    existing.append(int(n_part))
            except Exception:
                pass
        next_n = (max(existing) + 1) if existing else 1
        out_path = manifests_dir / f"selected_wave{next_n}_{nowstamp}.json"
    if not sel_dir.exists():
        print(f"選別ディレクトリが見つかりません: {sel_dir}")
        sys.exit(1)
    build_selected(sel_dir, man_path, out_path)

if __name__ == "__main__":
    main()
