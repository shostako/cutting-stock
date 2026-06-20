# PROGRESS — cutting-stock

> **2026-06-20 辞書式へ再構成（最終形）**: 一旦は段取り軸を分離して材料専用にし `pattern-stock` を作ったが、
> 切り方最小に現場価値があると判明し撤回。`solve()` を**辞書式2段**に再構成した:
> ① arc-flow で本数最小（gap=0 証明）→ ② CP-SAT 候補プール選択MIP で本数固定のまま切り方最小（証明付き）。
> 答えは単一解（トレードオフ/パレートUIは持たない）。`pattern-stock` は重複につき削除（旧二軸UIは git `f66f8d2`）。
> Wikipedia 例題で 73本/廃棄0.401%/切り方10通り を両方証明付きで到達（実測 2.6s）。以下の履歴は途中経緯を含む。

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
- 2026-06-18: **Wikipedia古典例で段取り軸の欠陥を検出 → ロバスト化A実装**（ブランチ `feat/setup-axis-robustness`）。材料軸は既知最適と完全一致（73本/0.401%/proven）で健全。段取り軸 config-B は出荷コードが `R=bars`（設計の R=types からドリフト）で重すぎ、CP-SATが解を返せず status=UNKNOWN→点が黙って消える**非再現・空出力**バグ（過去の「13を誤証明」報告はハルシネーションと判明）。修正3点: warm-start（材料解をヒント注入）/ R縮約（=P_mat, 最適≤P_matで証明保持・設計復帰）/ フォールバックanchor（点を落とさない）。結果: 完全再現・空にならない・z=73のP 13→12改善・前線が本物（12/8）・テスト55 green維持。**残る天井**: z=73のPは12止まり/proven立たず（90/300秒で不変）、既知最適10に未達＝config-Bは中小規模でも最適品質に届かない。詳細 `docs/SOLVER_DESIGN.md`「段取り軸の計算量天井とロバスト化」節 + `STATUS.md`。
- 2026-06-18: **B（再定式化）完了 = 候補プール選択MIPを主経路化**（`setup_mip.py`）。maximal パターン全列挙(`_enumerate_maximal_patterns`)→使用本数x_q・使用フラグy_qの線形MIP（Σx==bars, Σa·x≥d, min Σy, num_workers=1で決定論）。非凸積が消えtractable、maximal限定でも最適性不変（非maximalは含むmaximalへ同一本数で置換可）ゆえ全列挙が尽きれば真の最小に一致＝proven正当（cap5万超はconfig-B退避）。**z=73でP=10をproven到達**（config-Bの12止まり突破, Wikipedia既知最小10に一致）、z=74でP=8 proven、バイト完全再現。回帰 `solver/tests/test_benchmark.py`（maximal列挙単体＋Wikipedia既知最適突き合わせ, slow marker隔離）追加、既定スイート57 green。A+Bとも作業ブランチ `feat/setup-axis-robustness` 上、**未マージ・未デプロイ**（main/HF反映はユーザー確認後 `git push origin main && git push space main`）。
- 次の選択肢: スレッドC M6 複数原材料長（据え置き決定）/ 現状で一区切り。

## 確定事項

- 1D-CSP。Web GUI（React+Vite+TS）+ Python（HiGHS / OR-Tools）ソルバ核、両者は分離。
- 目的（2026-06-20 確定）: **辞書式2段** = ① 使用本数最小（材料最適）→ ② その本数で切り方(パターン種類数)最小。両方証明付き・**単一解**。トレードオフ/パレートは持たない。

## 次セッションへの引き継ぎ（最重要）

**現状（2026-06-20）: 辞書式に再構成＋GUI を現場向けに磨き込み、全て本番反映済み。機能的に一区切り、pending タスクなし。**

- **ソルバ**: `solve()` = 辞書式2段（① arc-flow on HiGHS で本数最小・gap=0証明 → ② `setup_mip` の CP-SAT 候補プール選択MIP で本数固定のまま切り方最小・証明）。`pareto.py` は廃止、答えは**単一解**。第2段は安全上限30s＋材料分解フォールバック。Wikipedia 例題で **73本/廃棄0.401%/切り方10通り** を両証明付き到達（約2.6s）。
- **GUI 磨き込み（全デプロイ済み）**: ラベル自動付与（長さ/英字/数字/手動・既定=長さ・長さ降順採番、`web/src/labels.ts`）、デモ3択（demo1=Wikipedia / demo2=既定kerf3 / demo3=ランダム）、帯ラベル拡大(15px)、開発者ジャーゴン撤去（記号L/k・Model A注記・ソルバ名表示）、ヘルスは異常時のみ警告、ライト/ダーク切替（OS追従・localStorage記憶・印刷はライト固定、`index.css` の `:root[data-theme="dark"]`）、スマホ対応（≤1024pxで1カラム）、見出し「計算結果」、「過剰生産なし」表示は削除。
- **姉妹 pattern-stock は削除済み**（辞書式で cutting-stock が両目的を内包＝重複）。旧二軸パレートUIは git 履歴 `f66f8d2` に残る。
- **デプロイ**: GitHub https://github.com/shostako/cutting-stock / HF https://shostako-cutting-stock.hf.space。**コード変更時は `git push origin main && git push space main` の両方**（HF push でリビルド）。**docのみ変更でも HF push で README が Space カードに反映される**。HF認証は GIT_ASKPASS（user=`shostako`, pass=`~/.cache/huggingface/token`）。**本ユーザーは cutting-stock では確認なしのデプロイを常時許可**（リモート作業で本番URLでしか確認できないため）。ただしデプロイ後の verify-by-effect（配信バンドルのハッシュ/新文字列フリップを curl ポーリング）は必須。
- **健全性**: `uv run pytest`（51件 + slow材料/辞書式ベンチ）/ `cd web && npm run build`。Playwright headless スクショ可（`~/.cache/ms-playwright`）。ローカル起動: 端末1 `uv run uvicorn solver.http:app --port 8000` / 端末2 `cd web && npm run dev`。
- 実装SSOT: ソルバ=`docs/SOLVER_DESIGN.md`（旧二軸パレートの記述はバナーで履歴扱い）/ GUI=`docs/GUI_DESIGN.md`＋`web/`。依存 highspy / ortools(snake_case) / fastapi / React+Vite+TS。

次の一手: 機能的には一区切り。追加の磨き込み or 新機能はユーザー指示待ち。
（未追跡: `docs/RESOLUTION-2026-06-18.md` = 段取り軸修正の記録。`setup_mip` 復活で内容は今も有効だが、リポに追跡するかは保留。）

既知の限界（将来詰めるなら）:
- 大規模域（types>10 等で maximal パターン列挙が `_POOL_CAP` 超）は config-B フォールバックに退避し、proven が立たない可能性。30s 上限超で材料分解にフォールバック（本数の最適性は常に保つ）。
- kerf 定義（Model A）の妥当性は crosscheck の射程外（両ソルバが同定義共有のため）。上位設計の前提。
