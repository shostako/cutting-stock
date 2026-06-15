# PROGRESS — cutting-stock

## 現在の状態

- 2026-06-15: labセッションで設計・スキャフォールド。独立gitリポ作成済み。
- 引き継ぎファイル一式作成済み: `CLAUDE.md`, `docs/SPEC.md`, `docs/PLAN.md`。
- 2026-06-15: **カット代の数え方を Model A（各取りに1カット, `Σℓ_j + m·k ≤ L`）で確定**し `docs/SPEC.md` に追記。初回コミット作成。
- 2026-06-16: **ソルバ核の設計を確定**（ultracode design phase）。独立3案×3レンズ審査→統合。`docs/SOLVER_DESIGN.md` に SSOT 化。
  - 材料軸 = Arc-flow MIP on HiGHS（gap=0証明）/ 段取り軸 = CP-SAT 設定モデルB（種類数の真の最小を証明）/ ε制約でパレート。
  - 敗者の CP-SAT 割当モデルを oracle.py に転用（arc-flow縮約のサイレント故障を CI で潰す保険）。
  - ユーザー確定: 2本立て(highspy+ortools) / 中小規模(列生成退路は仕込まない) / 常にgap=0まで粘る。
- 2026-06-16: **M0 セットアップ完了**。`uv add highspy ortools` + dev pytest、`solver/models.py`（dataclass群）、`solver/tests/test_smoke.py`（4件 green）。
  - 採用版: highspy 1.14.0 / ortools 9.15.6755 / Python 3.12.3。highspy高レベルAPIと CP-SAT（**snake_case が正**, PascalCaseは非推奨）の実在を本環境で裏取り済み。
- GUIは未着手。次は **M1 材料最適コア**（normalize → arcgraph → flow_mip → decompose）。

## 確定事項

- 1D-CSP、最適/準最適。Web GUI（React+Vite）+ Python（OR-Tools）ソルバ核、両者は分離。
- 主目的: 使用本数(=単一長なら廃棄量)最小。トレードオフ: 材料最適 vs 段取り(パターン種類数)最少。パレート前線を提示。

## 次セッションへの引き継ぎ（最重要）

このプロジェクトは別ディレクトリ（lab）のセッションから**会話を引き継がずに**始まる。
起動直後に `docs/PLAN.md` の「次のアクション」を読んで続行すること。

次の一手:
1. ~~カット代の数え方の定義を確定し `docs/SPEC.md` に追記。~~ → 完了（Model A 確定）。
2. ~~ソルバの設計を詰める（ウルトラコード）。~~ → 完了（`docs/SOLVER_DESIGN.md` に確定）。
3. ~~M0 セットアップ。~~ → 完了。
4. **M1 材料最適コア（単一原材料長）**: `normalize.py`（整数化・GCD縮約）→ `arcgraph.py`（arc-flowグラフ・対称性破り）
   → `flow_mip.py`（HiGHS で min 使用本数, gap=0）→ `decompose.py`（フロー分解→Pattern列）。`solve()` が材料最適 Solution を返す。
   SPEC検算例 + 小手計算で `bars_used` を手計算照合。（以降 M2→M7 は `docs/SOLVER_DESIGN.md` 参照。**M2/M7 がウルトラコード検証ゲート**）
