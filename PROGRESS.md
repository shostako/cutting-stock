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
- 2026-06-16: **M2 正当性検証（ウルトラコード）完了 = PASS**。oracle.py（CP-SAT割当 独立ground-truth）+ verify.py（crosscheck）実装。
  - ウルトラコード敵対検証（4攻撃面 + エージェント独自分）で**合計 ~14,259 + ~5,500 件**を突合。**arc-flow の normal-patterns 縮約による最適解の取りこぼしはゼロ**（bars_used が常に oracle/総当たり真最適と一致）＝縮約・フロー定式化・分解は健全。
  - 唯一の発見は**報告層のバグ**: `solve.py` の `proven_optimal` 判定が `mip_gap == 0.0` の厳密 float 比較で、LP下界が分数→HiGHS分枝時の machine-epsilon 残差（2e-16〜9e-14）を未証明と誤標記していた偽陰性。許容誤差 `< 1e-9`（`_GAP_TOL`）に修正。偽陰性インスタンスを回帰テストに昇格。
  - テスト 36件 green（smoke4 + material9 + oracle突合3 + 不変条件8 + proven_optimal回帰5 ほか）。
- 2026-06-16: **M3 段取り軸 + パレート完了**。`setup_mip.py`（CP-SAT 設定モデルB: 固定本数バジェット下のパターン種類数の真の最小を証明）+ `pareto.py`（z*..z*+B を ε制約掃引・非劣点抽出）。`solve(mode=pareto|material)` を ParetoFrontier に拡張。
  - 手検証トレードオフ例（L=8,{5:3,3:5}）で (z=4,P=2)→(z=5,P=1) を再現。実データでも z+1本で段取り4種→2種の解を提示。
  - proven フラグ正直: 材料最適点のみ bars_proven=True、各点 setup_proven は P が証明済み最小か。
  - テスト 43件 green（+ pareto 7件）。
- 2026-06-16: **M4 API/CLI境界完了**。`api.py`（唯一のJSON境界・dict<->dataclass・segments前計算）+ `cli.py`（stdin/stdout）+ `http.py`（FastAPI: /solve /validate /healthz）。
  - 入出力JSONスキーマは SOLVER_DESIGN.md「ローカルAPI」節準拠。segments は length合計=stock_length（Model A整合）。エラーコード INFEASIBLE/PIECE_TOO_LONG/INVALID_INPUT。
  - 依存追加: fastapi / uvicorn（runtime）、httpx（dev, TestClient用）。
  - テスト 54件 green（+ api 11件: スキーマ/segments不変/エラー/CLI/HTTP TestClient）。
- 2026-06-16: **M5 GUI コア完成**（GUIデザインは事前にウルトラコードでコンペ→可視化ファースト基線に統合, `docs/GUI_DESIGN` 相当は workflow 結果）。
  - `web/`: Vite+React+TS。チャートは全自前（棒=HTML絶対配置 width=len/L%で比率忠実・文字非歪み、散布図=SVG）。依存 react/react-dom のみ。
  - 実装: InputPanel / ParetoChart（散布図+スライダ+◇◆スナップ+下界線+退化前線対応）/ MetricsCard / PatternView+PatternBar（segments帯・色凡例・kerf最小視認幅）/ OptimalityBadge（厳密最適/材料準最適/gap・正直表示）。
  - dev proxy で http.py(:8000) に接続。フロントは本文 status/feasible で分岐。初期表示は実ソルバ出力フィクスチャ（バックエンド未起動でも全UI描画可）。
  - 実バックエンド接続でスクショ確認済み（材料最適6本/1.81%/4種 ⇄ 段取り最少7本/8.21%/2種 をスライダ即切替）。tsc型チェック+viteビルド通過。
- 2026-06-16: **M5 全完了**。M5-5 比較モード（材料最適と段取り最少を同一スケールで2レーン並置・共有凡例・狭幅縦積み）+ M5-6 磨き（stale淡色化バナー・Intl整形・未使用Vite初期アセット削除・web/README起動手順）。スクショ確認済み。tsc+viteビルド通過。
  - スナップ磁石吸着は設計どおり後回し（初版は最近接クリック+整数スライダ）。
- 2026-06-16: **スレッドA = GitHub 連携 完了**。ブランチ `master→main` リネーム、MIT `LICENSE` + ルート `README.md` 追加、`gh repo create --public` で https://github.com/shostako/cutting-stock に push。default=main / visibility=PUBLIC / license=mit 確認済み。`origin/main` 追跡。
- 2026-06-16: **スレッドB = スマホ用デプロイ 完了**。単一サーバ化（`http.py` が web/dist を存在時にルート mount、相対パスfetchで同一オリジン・CORS不要、dev時は mount せず vite proxy）+ `Dockerfile`（node build→python, uid1000, port7860）+ `.dockerignore`。**Hugging Face Spaces（Docker SDK, public, cpu-basic）にデプロイ**: https://huggingface.co/spaces/shostako/cutting-stock 、公開URL **https://shostako-cutting-stock.hf.space** （スマホ可）。git remote `space` 追加済み（再デプロイ= `git push space main`、HFトークンは `~/.cache/huggingface/token` に保持）。本番で `/healthz`（両ソルバload）・`/solve`（材料最適6本/1.81%/4種＝ローカル一致）・390px描画 確認済み。
  - HF用 frontmatter は README 冒頭に記載（GitHubはメタ表示するが無害）。トークンは Write 権限の `cutting-stock-deploy`（不要なら HF settings で revoke 可）。
- 2026-06-17: **M7 最終レビュー（ウルトラコード）完了**。6次元並列レビュー→敵対verify→統合（run `wf_9604ac3b-767`, 28エージェント, finding21 / 確定バグ9）。**ソルバ核は健全**＝材料最適性・Model A不変量（waste≥0/占有≤L/セグメント和=L）を 400+388 インスタンスで違反ゼロ。判定FAILの実体は計算誤りでなく「JSON境界の入力検証・タイムアウト劣化・廃棄量計上」。
  - **bug#2 廃棄量メトリクス反転（既定パレート経路で発火）を修正**: 過剰生産ピースの占有計上で z 増→廃棄減の非単調（SPEC.md:52違反）だったのを `z·L − 総需要長`（kerf・端材・過剰生産含み z に単調）に統一（`solve.py`/`pareto.py`）。回帰 `test_pareto_waste_monotonic_spec52` 追加、テスト55件 green。
  - 残り確定バグ8件（全て off-default パス＝異常入力/不正オプション、既定GUIでは未発火）＋本質的限界＋カバレッジギャップは `docs/SOLVER_DESIGN.md`「M7最終レビュー結果」節に文書化。**ユーザー判断 2026-06-17: #2のみ修正、残りは文書化のみ。**
- 次の選択肢: スレッドC M6 複数原材料長（据え置き決定）/ 現状で一区切り。

## 確定事項

- 1D-CSP、最適/準最適。Web GUI（React+Vite）+ Python（OR-Tools）ソルバ核、両者は分離。
- 主目的: 使用本数(=単一長なら廃棄量)最小。トレードオフ: 材料最適 vs 段取り(パターン種類数)最少。パレート前線を提示。

## 次セッションへの引き継ぎ（最重要）

**復帰手順（2026-06-17, M0-M5完了 + M7最終レビュー完了。M6のみ据え置き）:**
- **M0-M5 全完了 + M7 完了**。エンドツーエンドで動く・本番稼働中。テスト55件 green。
  - **A: GitHub push** — ✅完了（public/MIT, main, https://github.com/shostako/cutting-stock）。
  - **B: スマホ用デプロイ** — ✅完了（HF Spaces, https://shostako-cutting-stock.hf.space 稼働中。再デプロイ= `git push space main`）。
  - **M7 最終レビュー（ウルトラコード）** — ✅完了（2026-06-17）。ソルバ核健全、bug#2のみ修正、残り8件は off-default パスとして文書化。詳細 `docs/SOLVER_DESIGN.md`「M7最終レビュー結果」節（未修正バグの所在表＝将来直すときの地図）。
  - **C: M6 複数原材料長** — **据え置き（ユーザー決定 2026-06-17: 締めに回す）**。再開するなら確定方針は `docs/SOLVER_DESIGN.md` M6 節（材料目的=総廃棄最小 / 在庫上限+無制限両対応 / 段取り軸もフル / API要素1後方互換）。**ユーザー指示: M6でエラーになったら捨てて次へ、深追いしない。**
- 注意: HF Space は `origin/main`（GitHub）と同期させたい。**コード変更時は `git push origin main && git push space main` の両方**（HF push でリビルド走る。docのみ変更はHF push不要）。
- 健全性確認: `uv run pytest`（54件） / `cd web && npm run build`。dev サーバ背景稼働の可能性（:8000/:5173, 落ちてたら `docs/GUI_DESIGN.md` 末尾手順で再起動）。
- 実装SSOT: ソルバ=`docs/SOLVER_DESIGN.md` / GUI=`docs/GUI_DESIGN.md`＋`web/`。依存 highspy1.14 / ortools9.15(snake_case) / fastapi / React+Vite。

次の一手:
1. ~~カット代の数え方の定義を確定し `docs/SPEC.md` に追記。~~ → 完了（Model A 確定）。
2. ~~ソルバの設計を詰める（ウルトラコード）。~~ → 完了（`docs/SOLVER_DESIGN.md` に確定）。
3. ~~M0 セットアップ。~~ → 完了。
4. ~~M1 材料最適コア。~~ → 完了（arc-flow on HiGHS, gap=0, テスト13件 green）。
5. ~~M2 正当性検証（ウルトラコード）。~~ → **PASS**（縮約の最適解取りこぼしゼロ／report層のfloat比較バグを1件修正）。
6. ~~M3 段取り軸 + パレート。~~ → 完了（setup_mip + pareto, トレードオフ再現）。
7. ~~M4 API/CLI境界。~~ → 完了（api/cli/http, 54テスト green）。サーバ起動: `uv run uvicorn solver.http:app`。
8. ~~M5 GUI コア。~~ → 完成（Vite+React+TS, 自前チャート, パレート連動, 正直バッジ）。起動: 端末1 `uv run uvicorn solver.http:app --port 8000` / 端末2 `cd web && npm run dev`。
   （Playwrightスクショ用に headless chromium + Noto CJK を環境に導入済み。`~/.cache/ms-playwright` に build1200→1228 symlink）
9. ~~M5 仕上げ（比較モード+磨き）。~~ → 完了。
10. **次の選択肢（ユーザー判断）**:
   - M6 複数原材料長（arcgraphをL引数化しS並置・需要横断充足。**既定材料目的を要確認**）
   - **M7 最終レビュー（ウルトラコード検証ゲート）**: 正確性・性能・エッジ・UIを次元分けで敵対検証
   - 本番デプロイ/配布、または現状で一区切り

検証の取りこぼし（M3前/M7で塞ぐと堅い、PASS判定のスコープ外）:
- 大規模域（types>10, qty>25, ビン数>16）は oracle/総当たりが証明不能で未踏。縮約の正しさは規模非依存の構造性質なので PASS は保つ。
- PIECE_TOO_LONG 経路は committed テストで確認済みだが掃引では未発火（正常系集中）。
- kerf 定義（Model A）の妥当性は crosscheck の射程外（両ソルバが同定義共有のため）。上位設計の前提。
