# Final 1000 Trait Schema

## 目的
`manifests/final_1000_manifest_v1.json` の属性定義を固定し、UI表示・on-chain metadata・検証の解釈を統一する。

## 固定属性（5項目）
1. `Pattern`
2. `Color Variation` (`palette_id`)
3. `Collar` (`none` / `checkered_collar` / `classic_red_collar`)
4. `Rarity Tier` (`common` / `rare` / `superrare`)
5. `Rarity Type` (`none` / `odd_eyes` / `red_nose` / `blue_nose` / `glasses` / `sunglasses` / `corelogo` / `pinglogo`)

## superrare 固定ルール
- `Rarity Tier = superrare` の2体のみ対象。
- 次を固定値として扱う:
  - `Pattern = superrare`
  - `Color Variation = superrare`
  - `Collar = none`
  - `Rarity Type = corelogo` または `pinglogo`

## 内部データとの切り分け
- canonical manifest item には内部検証用に `collar` 真偽値と `collar_type` が残る。
- ただし公開 metadata / viewer attributes では冗長な `with_collar` / `without_collar` を出さず、`Collar` を `none` / `checkered_collar` / `classic_red_collar` の1項目として扱う。

## Pattern / Color Variation と実画の関係
- `Pattern` は模様テンプレート名。
- `Color Variation` (`palette_id`) はカラーパレット系列名。
- ただし、見た目の最終色配置は `pattern` ごとのスロット構造により決まるため、`pattern + palette_id` だけで完全一意にはならない。
- 再現性は以下を併用して担保する:
  - `pattern`
  - `palette_id`
  - `color_tuple`
  - `variant_key`
  - `slots`
  - `layers_24`

## 実装上の正本
- 生成: `scripts/build_final1000_manifest.py`
- 検証: `scripts/validate_final1000_manifest.py`
- 集計: `scripts/summarize_final1000_traits.py`

## 表示ラベル方針（内部IDと分離）
- 内部ID（manifestの値）は機械処理向けに固定する。
  - 例: `common`, `superrare`, `checkered_collar`
- UI表示ラベルは人間向けに変換して表示する。
  - `common` -> `Common`
  - `rare` -> `Rare`
  - `superrare` -> `Super Rare`
  - `checkered_collar` -> `Checkered Collar`
  - `classic_red_collar` -> `Classic Red Collar`
  - `odd_eyes` -> `Odd Eyes`
  - `red_nose` -> `Red Nose`
  - `blue_nose` -> `Blue Nose`
  - `corelogo` -> `Core Logo`
  - `pinglogo` -> `Ping Logo`
- 正式な表示ラベル定義: `manifests/trait_display_labels_v1.json`
