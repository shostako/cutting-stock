# GUI 設計（SSOT — 現行）

> **実装済みの SSOT は `web/` のコード**。本書は採用デザインの要約と開発手順。
> 設計経緯（ultracode 3案コンペ、旧パレート/比較モードUI）は `docs/history/GUI_DESIGN-2026-06.md`。

## 現行 GUI（辞書式・単一解）

ソルバが単一解を返すため、GUI に解の切替・トレードオフ UI はない。

- **レイアウト**: デスクトップ2カラム（左=入力+計算結果メトリクス、右=カットパターン群）。≤1024px で1カラム。
- **棒グラフ**: 各 `segment` を `left=offset/L%`, `width=length/L%` の HTML 絶対配置で描画（比率忠実・文字非歪み）。
  `kind` で色分け: piece=長さ別パレット（`colors.ts`, 同じ長さは常に同色）/ kerf=濃灰・`min-width` で最小視認 /
  waste=灰。同一パターンは `run_count` で「×N本」まとめ表示。チャートは全自前、依存は react/react-dom のみ。
- **正直表示**: `OptimalityBadge` — 「本数は最少（確認済み）」（緑, `proven_optimal`）と
  「切り方も最小（確認済み）」（青, `patterns_min_proven`）。証明できない時はバッジを出さない。生ソルバ status は出さない。
- **入力**: 原材料長・カット代（初期設定）+ 需要テーブル（長さ/本数/ラベル）。
  ラベル方式は 長さ / A,B,C / 1,2,3 / 手動 の4スキーム（`labels.ts`, 採番は長さ降順）。
- **デモ**: demo1=Wikipedia 板取り代表例（73本/切り方10通りの既知最適）、demo2=ランダム生成（押すたび変化）。
- **現場向け出力**: 印刷（カット指示書ヘッダ付き）/ CSV 書き出し（BOM付きUTF-8, Excel互換, `report.ts`）。
- **過剰生産テーブル**: ソルバが需要 == で解くため正常系では出ない。ソルバが約束を破った時だけ現れる安全網
  （`computeProduction` がフロント側で独立に検算）。
- **その他**: stale淡色化バナー（入力変更後）/ ライト・ダーク切替（OS追従・localStorage記憶）/
  バックエンド未起動でも `fixtures.ts` で全UI描画（フィクスチャは `web/scripts/gen_fixtures.py` で再生成、手編集禁止）。
- フロントは本文 `status`/`feasible` で分岐（/solve は常に HTTP200）。

## 開発手順

- 起動: 端末1 `uv run uvicorn solver.http:app --host 127.0.0.1 --port 8000` / 端末2 `cd web && npm run dev`（:5173, proxy 経由）。
- テスト: `cd web && npm test`（vitest, ロジック層）/ `python3 web/e2e/smoke.py`（E2E, 要 build）。詳細 `web/README.md`。
- スクショ: Playwright（headless chromium + Noto CJK 導入済み）。日本語が豆腐なら `sudo apt-get install -y fonts-noto-cjk`。
  ブラウザ build 番号ズレ時は `~/.cache/ms-playwright` に `chromium_headless_shell-<期待>` → 実体 の symlink。
