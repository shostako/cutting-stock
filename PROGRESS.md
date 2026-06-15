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
- 2026-06-16: **M1 材料最適コア完了**。`normalize` / `bounds` / `errors` / `arcgraph` / `flow_mip` / `decompose` / `solve` 実装。
  - arc-flow MIP on HiGHS で使用本数最小を gap=0 厳密に解く。canonical order（de Carvalho）で対称性破り。
  - フロー分解→Patternグルーピング、Optimality（mip_gap + LP独立下界の二重裏取り）添付。
  - テスト 13件 green（smoke 4 + material 9）。連続下界 ≤ 使用本数 ≤ FFD上界 のサンドイッチで最適性を裏取り。
- GUIは未着手。次は **M2 正当性検証（ウルトラコード）**: oracle.py（CP-SAT割当直接解）× arc-flow 突合の CI 化、BPPLIB ベンチ、kerf不変条件 property test。**arc-flow縮約のサイレント故障をここで潰す**。

## 確定事項

- 1D-CSP、最適/準最適。Web GUI（React+Vite）+ Python（OR-Tools）ソルバ核、両者は分離。
- 主目的: 使用本数(=単一長なら廃棄量)最小。トレードオフ: 材料最適 vs 段取り(パターン種類数)最少。パレート前線を提示。

## 次セッションへの引き継ぎ（最重要）

**コンパクト直後の復帰手順（2026-06-16, M1完了時点で context compact 実施）:**
1. `docs/SOLVER_DESIGN.md` を読む（SSOT, ハイブリッド設計＋実装マイルストン M0-M7）。M0/M1 は実装済み。
2. 末尾の **「M2 検証計画（ウルトラコード）」節**がそのまま M2 の作業ブリーフ。これを workflow 化して撃つ。
3. ユーザーは復帰後に **M2 をウルトラコードで実施**する意図（このターンで予告済み）。`続けて` 等の合図で M2 ウルトラコードを起動する。
4. 実装基盤: `uv run pytest` で現状13件 green を確認してから着手。依存は highspy 1.14.0 / ortools 9.15.6755（snake_case API が正）。

次の一手:
1. ~~カット代の数え方の定義を確定し `docs/SPEC.md` に追記。~~ → 完了（Model A 確定）。
2. ~~ソルバの設計を詰める（ウルトラコード）。~~ → 完了（`docs/SOLVER_DESIGN.md` に確定）。
3. ~~M0 セットアップ。~~ → 完了。
4. ~~M1 材料最適コア。~~ → 完了（arc-flow on HiGHS, gap=0, テスト13件 green）。
5. **M2 正当性検証（ウルトラコード, 次にやる）**: `docs/SOLVER_DESIGN.md`「M2 検証計画」に従い、
   `oracle.py`（CP-SAT 割当直接解）× arc-flow 目的値一致を敵対的に裏取り。BPPLIB 既知最適突合・kerf不変条件 property test。
   **arc-flow縮約のサイレント故障をここで潰す**。緑になるまで M3（段取り軸）に進まない。
   （以降 M3→M7 は `docs/SOLVER_DESIGN.md` 参照。**M2/M7 がウルトラコード検証ゲート**）
