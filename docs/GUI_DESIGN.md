# GUI 設計（確定）— M5

> **2026-06-20 注**: トレードオフ2択トグル・余分本数の高度モード・パレート/比較モードUIは廃止。現在の GUI は
> 辞書式の**単一解**（本数最小→切り方最小）＋カット指示書（印刷/CSV）＋過剰生産表示＋2段の最適性バッジのみ。
> 以下のトレードオフ / パレート / 比較モードに関する記述は旧設計の履歴。

> GUIデザインは独立3案（情報密度 / 操作フロー / 可視化リッチ）をウルトラコードで競わせ、
> 3レンズ（使いやすさ / 実装容易性 / 射出成形現場の実用性）の審査で統合して決定（run `wf_fce5fc4b-c72`）。
> **実装済みの SSOT は `web/` のコード**。本書は採用デザインの要約と M5 残作業仕様。

## 採用デザイン（可視化ファースト基線 + 接ぎ木）

判定: 可視化リッチ案が総合1位（現場実用性8・実装容易性7）。これを基線に、ダッシュボード案の
**2解並置比較モード**と、ウィザード案の**退化前線明示・現場語ラベル・stale淡色化**を接ぎ木。

- **レイアウト**: デスクトップ2カラム。左=操作（入力＋パレート散布図＋スライダ＋メトリクス）、右=主役（比率忠実バー群）。狭幅(<1024px)で1カラム。
- **棒グラフ**: 各 `segment` を `left=offset/L%`, `width=length/L%` の HTML 絶対配置で描く（比率忠実・文字非歪み）。`kind` で色分け（piece=長さ別パレット / kerf=濃灰・`min-width`で最小視認 / waste=灰ハッチ）。同一パターンは `run_count` で「×N本」まとめ。
- **パレート**: 自前SVG散布図（x=P, y=z, ◇材料最適/◆段取り最少/●選択/○他, 下界破線）+ スライダ「材料最優先↔段取り最少」+ ◇◆スナップボタン。`selectedIndex` を散布図/スライダ/メトリクス/帯で共有、再計算ゼロで即切替。退化前線(1点)は明示。
- **正直表示**: `OptimalityBadge`=厳密最適(緑)/材料準最適(灰)/gap(黄)、`SetupBadge`=段取り証明(青)/段取り上界。生ソルバstatusは出さない。
- **技術**: Vite + React + TS、チャート全自前（ライブラリ無し=比率を1pxも崩さない）、状態は useState のみ、依存 react/react-dom のみ。dev proxy で `http.py(:8000)` に接続。フロントは**本文 `status`/`feasible` で分岐**（/solve は常に HTTP200）。初期表示は実ソルバ出力フィクスチャ（`web/src/fixtures.ts`、バックエンド未起動でも全UI描画可）。

## 実装済み（M5-1〜M5-4 + 正直表示）

`web/src/` : `api/types.ts` `api/client.ts` `colors.ts` `fixtures.ts` `App.tsx` `App.css` `index.css`、
`components/` 配下 `InputPanel` `ParetoChart` `MetricsCard` `PatternView` `PatternBar` `OptimalityBadge`。
tsc型チェック + vite build 通過。実バックエンド接続でスクショ確認済み（材料最適6本/1.81%/4種 ⇄ 段取り最少7本/8.21%/2種）。

## 残作業（次にやる = ユーザーは選択肢「1」を選択）

### M5-5 比較モード（2解並置）
- 右カラム上部に「比較モード」トグル。ON で右を上下2レーンに分割し、**材料最適解(material_optimal_idx)** と
  **段取り最少解(setup_optimal_idx)** の帯を**同一 viewBox/同一CSS幅=同一スケール**で並置（端材の多寡を一目比較）。
- 各レーンに使用本数/種類/廃棄率/バッジ。散布図はその2点を固定強調。狭幅では縦2段積みにフォールバック。
- 現場の核心判断「2案をА/B比較」を成立させる（可視化案単独の弱点だった2解同時比較を解消）。

### M5-6 磨き（後回し可）
- 数値整形 `Intl.NumberFormat('ja-JP')`、廃棄率2桁。
- スナップ磁石吸着（初版は最近接クリック+整数スライダのみ。ジッタ回避で後付け）。
- 入力変更後の stale 淡色化バナー（前結果は破棄しない）+ debounce validate の即時実行可否表示。
- `web/README.md` に起動手順、未使用の Vite 初期アセット（`src/assets/*`, `public/icons.svg` 等）削除。
- 狭幅1カラムの作り込み（現状CSSフォールバックはあるが要確認）。

## 起動・スクリーンショット手順

- 起動: 端末1 `uv run uvicorn solver.http:app --host 127.0.0.1 --port 8000` / 端末2 `cd web && npm run dev`（:5173, proxy 経由で :8000）。
- スクショ: Playwright MCP（headless chromium + Noto CJK 導入済み）。日本語が豆腐なら `sudo apt-get install -y fonts-noto-cjk`。
  ブラウザ build 番号ズレ時は `~/.cache/ms-playwright` に `chromium_headless_shell-<期待>` → 実体 の symlink。
