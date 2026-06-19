# ソルバ核 設計（確定）

> **2026-06-20 注**: 段取り軸（`setup_mip.py` = CP-SAT パターン種類最小化）と `pareto.py` は本リポから削除し、
> 姉妹プロジェクト `pattern-stock` へ分離した。以下の段取り軸 / パレート掃引に関する設計記述は分離前の履歴。
> 本リポは材料軸（arc-flow MIP on HiGHS, gap=0 証明）のみ。`oracle.py`（独立 CP-SAT 検証）は材料軸の保険として残置。

> 本ドキュメントは実装の SSOT。`docs/SPEC.md`（問題仕様）と `docs/PLAN.md`（ビルド方針）を前提とする。
> 設計は独立3案（列生成B&P / CP-SAT直接 / arc-flow ILP）を競わせ、3レンズ（最適性・実装可能性・アーキ）の
> 審査パネルで統合して決定した（ultracode design phase, run `wf_62442123-8a4`）。

## 決定サマリ

軸ごとに最強ツールを割り当てる**ハイブリッド**。勝者総取りはしない。

- **材料軸（使用本数 = 単一長なら廃棄量）= Arc-flow MIP on HiGHS**。Model A の実効幅 `w_i = ℓ_i + k` を
  弧長にすれば占有長制約 `Σℓ_j + m·k ≤ L` が「0→L の経路長 ≤ L」に素直に化ける。`gap=0` 厳密証明。
- **段取り軸（パターン種類数 P）= CP-SAT 設定モデルB**。候補プール非依存で**種類数の真の最小を「証明」できる
  3案唯一の手段**。フロー分解/列生成のプール固定 selection-MIP は上界しか出せず、ツールの目玉が構造的に弱くなる。
- **CP-SAT 割当モデルを `oracle.py` に転用**（敗者案の再利用）。arc-flow 最大の地雷＝対称性破り縮約の
  サイレント最適解取りこぼしを、CI で目的値一致アサートして潰す保険。
- パレートは **ε制約（整数本数バジェット `z*..z*+B` 掃引）** で両軸を束ねる。

### ユーザー確定事項（2026-06-16）

| 論点 | 決定 |
|---|---|
| ライブラリ構成 | **2本立て `highspy`（材料軸）+ `ortools`/CP-SAT（段取り軸+オラクル）**。依存は3ファイルに局所化 |
| 想定問題規模 | **中小規模**（distinct長 ≲20, 総本数 ≲数百）。mm単位、L=数千mm想定。**列生成への退路は初期に仕込まない** |
| 最適性/応答方針 | **常に gap=0 まで粘る**（正確性優先）。`time_limit` は安全天井（既定は十分大 or 無制限）。万一到達時は gap を正直表示し OPTIMAL を詐称しない |

カット代は Model A 確定（`docs/SPEC.md`「カット代の数え方（確定）」）: `Σℓ_j + m·k ≤ L`、実効幅 `ℓ_j+k`、容量 `L`。

## アーキテクチャ（I/O 完全分離・純関数核・依存3ファイル局所化）

```
solver/
  __init__.py
  models.py     # 純dataclass(frozen)・依存ゼロ。StockSpec/DemandItem/Problem/Pattern/Solution/Optimality/ParetoFrontier
  normalize.py  # 整数化・GCD縮約・復元（純関数, 冪等）
  bounds.py     # continuous_lower_bound, validate_input(退化入力検出), ffd_initial(貪欲上界/ヒント)
  arcgraph.py   # arc-flowグラフ構築（頂点・弧・対称性破り/reachable集合）。ソルバ非依存・純関数
  flow_mip.py   # ★highspy依存。arc-flow材料最適MIP + LP下界
  decompose.py  # フロー分解 → Pattern列（純関数）
  setup_mip.py  # ★ortools(CP-SAT)依存。設定モデルB（パターン種類数最小, ε制約点）
  oracle.py     # ★ortools(CP-SAT)依存。割当モデル直接解（小規模ground-truth, CIクロスチェック）
  pareto.py     # フェーズ1+2を束ね z*..z*+B 掃引 → ParetoFrontier（オーケストレータ）
  benchmark.py  # BPPLIBローダ + 既知最適突合レポート
  solve.py      # 公開エントリ solve(problem) -> ParetoFrontier（唯一の外部ロジック入口）
  api.py        # 唯一のJSON境界。dict <-> dataclass 変換のみ。ソルバ非依存
  cli.py        # argparse薄ラッパ → api.solve_from_json(stdin) -> stdout
  http.py       # FastAPI薄ラッパ。api.solve() を叩くだけ
  tests/
```

**境界**: `solve.py` 以下は純Python + (highspy/ortools) のみ。print/file/HTTP なし。`Problem` を受けて
`ParetoFrontier` を返すだけ＝冪等・副作用ゼロ。`api.py` より上（cli/http/将来desktop/batch）は dict のみ。
ソルバ依存は `flow_mip` / `setup_mip` / `oracle` の3ファイルに閉じる。これで CLAUDE.md 4原則
（冪等・リトライ安全・エラーハンドリング・原子性）を構造で満たす。

## 材料軸: Arc-flow MIP on HiGHS

1. **正規化**（`normalize.py`）: `ℓ_i, k, L` を整数化し GCD `g` で割って `L' = L/g` に縮約（グラフ縮小・冪等性、復元時 ×g）。
   前処理で `ℓ_i + k > L` は MIP に渡す前に `PIECE_TOO_LONG` で弾く（原子性）。
2. **グラフ**（`arcgraph.py`）: 頂点 `V = {0..L'}`。item弧 `d → d+w_i`（`w_i = (ℓ_i+k)/g`）、loss弧（詰め切り頂点→`L'`）。
   de Carvalho normal patterns / reachable集合 BFS で弧数を `O(L'·n)` に抑える。**この縮約が最大の実装難所** → `oracle.py` の CI が必須の保険。
3. **MIP**（`flow_mip.py`, HiGHS via `highspy`）: フロー保存（各内部頂点）+ 需要充足（`Σ item弧フロー ≥ d_i`）。
   feedbackフロー = 使用本数 `z`。目的 `minimize z`。`addVariable(type=kInteger)` / `addConstr` / `minimize` / `run`。
   `getInfo().mip_gap` と `modelStatus` で証明。
4. **分解**（`decompose.py`）: 解 `x_a` をフロー分解 → 0→L 経路 = 各原材料1本のカットパターン。経路上の item弧の並び = 物理カット順（可視化のx座標）。

## 段取り軸: CP-SAT 設定モデルB

> 2026-06-18 更新: 実装の主経路は**候補プール選択MIP**に置換（config-Bはこの定式化が中規模でも
> 最適到達できないため大規模フォールバックへ降格）。最新は「段取り軸の計算量天井とロバスト化」節参照。本節は当初設計。

物理ビンでなく**パターンスロット**を変数化（候補プール非依存＝真の最小を証明可能）。
- `s_used[p] ∈ {0,1}`、`c[p,j] ∈ [0, L//w_j]`（パターン内容を自由変数化）、`n[p] ∈ [0, Nb]`。
- 妥当パターン: `Σ_j w_j·c[p,j] ≤ L`。リンク: `s_used[p] ≤ n[p] ≤ Nb·s_used[p]`。
- 本数バジェット: `Σ_p n[p] == Nb`（= パレート制御変数）。
- 需要: `z[p,j] = add_multiplication_equality(n[p], c[p,j])`; `Σ_p z[p,j] ≥ d_j`。
- 対称性破り: `s_used[p] ≥ s_used[p+1]`。スロット数 `R` = types を初期値、不足なら `2·types`。
- 目的: `minimize Σ_p s_used[p]`。

## パレート（ε制約・整数本数バジェット掃引）

NP困難な P 最小化を「定数回（B+1回）の有界MIP」に分解するのが tractability の核。
1. フェーズ1（arc-flow）で材料最適 `z*` を厳密に求める（gap=0 + LP下界切り上げの二重裏取り）。
2. 前線レンジを `z*..z*+B` に限定（既定 **B=3**, GUI可変）。round-up property より有用な段取り削減は数本緩めた範囲で起きる。
3. 各 `z = z*+t` について設定モデルBを `Σ_p n[p]==z` 固定で解き、最小種類数 `P*(t)` を得る（証明付き）。
4. 点列 `{(z, P*(t))}` の非劣点（z増で P が真に減る点）だけ残す → パレート前線。z昇順 = P降順 = GUIスライダindexに1:1。

**フォールバック**: 設定モデルBが types大で安全天井に当たる場合のみ、arc-flow経路+FFD生成の候補プール上の
selection-MIP に退避し、その点は「P ≤ k, gap付き上界」と明示。UI で「証明済みOPTIMAL」と「上界（プール依存）」を
バッジで区別し詐称しない。（※今回の想定規模＝中小では本フォールバックは基本発動しない見込み。）

## 整数化・最適性・不変条件

- 材料軸/段取り軸とも**最初から整数MIP/CPで直接解く**（LP緩和は下界算定にのみ使う）。
- **二重裏取り**: 材料軸は (a) `status==Optimal かつ mip_gap < 1e-9`（**float 許容誤差で判定**）、(b) LP緩和を別途解き
  `z_int ≥ ⌈z_LP⌉` を確認。両者一致で round-up property 成立＝ソルバ自己申告に依存しない第2証拠。
  段取り軸は `status==OPTIMAL` かつ `best_objective_bound==objective_value`。
  > ⚠ M2 検証の知見: `mip_gap == 0.0` の**厳密比較は誤り**。HiGHS は LP下界が分数のインスタンスで分枝後、
  > status=Optimal を返しつつ mip_gap に machine-epsilon 残差（2e-16〜9e-14）を残す。`solver/solve.py` は
  > 許容誤差 `< 1e-9`（定数 `_GAP_TOL`）で判定する（float 等価比較アンチパターンの回避, CLAUDE.md tool-design-principles）。
- **Optimality データ**（全解に必ず添付, ネスト dataclass）: `Optimality(status, mip_gap, lp_lower_bound, proven_optimal, setup_proven, timed_out)`。
  `proven_optimal` は `status==Optimal かつ mip_gap < 1e-9` のときだけ True。`OPTIMAL` を名乗るのも同条件。
- **kerf不変条件（必須 property test）**: 全パターンで `Σℓ_j + m·k ≤ L` と `waste = L − Σℓ − m·k ≥ 0`。
  総量保存 `z·L = Σℓ充足 + Σkerf + Σwaste`。
  ※提案段階で出た例 `990×3 @ L=2995,k=10`（占有3000>2995, waste=−5）は本不変条件違反。**実装はこれをハードに弾く**。

## データモデル（`models.py`）

- `Pattern`: `cuts: tuple[int,...]`（物理カット順=棒グラフx座標）+ `item_counts: dict[length->本数]` の両持ち。
  `stock_length` を最初から持たせ複数長拡張に備える。`waste` / `run_count`。
  （positional tuple の counts は需要リスト順序依存の地雷なので**採らない**）
- `Solution`: `bars_used(z)`, `patterns`, `total_waste`, `waste_ratio`, `num_pattern_types(P)`, `optimality: Optimality`。
- `ParetoFrontier`: `solutions`（z昇順=P降順）, `material_optimal_idx`, `setup_optimal_idx`, `recommended_index`。

## ローカルAPI（cli stdin/stdout と http が共有する単一スキーマ）

入力:
```json
{
  "stock": { "length": 2995, "kerf": 10 },
  "demand": [ { "length": 990, "qty": 4, "label": "A" }, { "length": 560, "qty": 6, "label": "B" } ],
  "options": { "mode": "pareto", "max_extra_bars": 3, "time_limit_sec": null, "rel_gap": 0.0, "workers": 8 }
}
```
（`mode`: material | setup | pareto。複数長拡張時は `stock` を `stocks:[{length,kerf,cost,available}]` に＝要素1で後方互換）

出力（`ParetoFrontier` 直列化）の要点:
- トップ: `status`(OK|INFEASIBLE|ERROR), `validation`[], `input_echo`, `lower_bound_bins`, `pareto`, `meta`。
- `pareto.solutions[]`: `bars_used`, `total_waste`, `waste_ratio`, `num_pattern_types`,
  `optimality{mip_gap, lp_lower_bound, proven_optimal, setup_proven, status, timed_out}`, `patterns[]`。
- `patterns[].segments[]`: `{kind: piece|kerf|waste, offset, length, item_length, label}`。
  **`segments` の length 合計 = `stock_length` が常に成立**（Model A 整合不変量・kerf込み, 整合検証に使う）。
- エンドポイント: `POST /solve`(同期) / `POST /validate`(feasibilityのみ) / `GET /healthz`。
  エラー時 `{"status":"ERROR","error":{"code":"INFEASIBLE|PIECE_TOO_LONG|INVALID_INPUT","message":...}}`。
- CLI と HTTP は同じ `api.solve` を呼ぶ＝振る舞い一致保証。

## 可視化契約

- **棒グラフ**: `Pattern → segments` を API 側で前計算（フロント数値演算ゼロ）。`offset`/`length` をピクセルに線形マップするだけ。
  同一パターンは `run_count` 本まとめ表示（「×12本」）。色: piece=長さ別カラースケール, kerf=細い区切り線, waste=グレー。
- **パレート切替**: `solutions`（z昇順=P降順）を散布図（x=P, y=z）。点クリック→棒グラフ群へ即切替（再計算不要、全点を一度に返す）。
  `material_optimal_idx`/`setup_optimal_idx` をスナップ点、`recommended_index` を初期選択。スライダ=frontier index 移動。
- **正直表示**: 各点に Optimality バッジ（緑「厳密最適」/ 黄「gap g% 上界」）。段取り軸の証明点とフォールバック上界を区別。
  `lower_bound` を前線図に基準線として重ねる。

## 実装マイルストン（単一原材料長から、各Mでテスト緑を保ち冪等に積む）

- **M0 セットアップ（ソロ）** ✅ **完了（2026-06-16）**: `uv add highspy ortools` + dev pytest。`models.py` の dataclass 定義。
  スモークテストで API 実在を**本環境で裏取り**済み（`solver/tests/test_smoke.py`, 4件 green）。確定事項:
  - 採用バージョン: `highspy 1.14.0` / `ortools 9.15.6755` / Python 3.12.3 / uv 0.11.7。
  - highspy 高レベル API（`addVariable(type=HighsVarType.kInteger)` / `addConstr` / `minimize` / `getModelStatus()==kOptimal` / `getInfo().mip_gap` / `val`）は設計想定どおり実在。
  - **ortools は snake_case が正**（`new_int_var` / `add_multiplication_equality` / `solve` / `value` / `best_objective_bound` / `objective_value`）。PascalCase（`AddMultiplicationEquality` 等）は 9.15 で**非推奨**＝実装は snake_case を使う。
- **M1 材料最適コア（ソロ）**: normalize → arcgraph（対称性破り含む）→ flow_mip → decompose。`solve()` が材料最適 Solution を返す。
  SPEC 検算例（L=2995, ℓ=990, k=10 → m=2）+ 小手計算で `bars_used` を手計算照合。
- **M2 正当性検証（ウルトラコード）**: `oracle.py`（CP-SAT割当直接解）→ arc-flow×CP-SAT クロスチェックを CI 化。
  BPPLIB（Falkenauer U/T, Hard28）取込・既知最適突合。kerf不変条件 property test。**arc-flow縮約のサイレント故障をここで潰す**。
  これが緑になるまで段取り軸に進まない。
- **M3 段取り軸 + パレート（ソロ）**: `setup_mip.py`（設定モデルB）→ `pareto.py`（z*..z*+B 掃引・非劣点抽出）。
  `P_min` を小規模総当たりと照合。`ParetoFrontier` を返す。
- **M4 API/CLI境界（ソロ）**: `api.py` + segments前計算 + `cli.py` + `http.py`(FastAPI)。入出力JSONスキーマ確定。エラーコード整備。
- **M5 GUI（React+Vite, ソロ / GUI設計は任意ウルトラ）**: 棒グラフ + パレート散布図/スライダ + メトリクス + Optimality バッジ。
- **M6 複数原材料長拡張（段階・後続）**: arcgraph を L 引数化のまま S回呼びグラフ並置＋需要横断充足。
  data model は `stock_length` + 将来の cost/available を見越し済み。M1 のテストが要素1退化で緑のままを回帰保証。
  **ユーザー確定方針（2026-06-16）:**
  - 材料目的 = **総廃棄（材料量）最小** = `min Σ_s (L_s × 使用本数_s)`（材料軸の重み w_s = L_s。単一長なら本数最小に退化）。
  - 原材料制約 = **在庫上限あり ＋ 無制限の両対応**（各 stock に `available: int|None`。None=無制限、整数=`Σ flow(source_s) ≤ available_s`）。
  - スコープ = **段取り軸・パレートもフル複数長対応**（setup_mip の各スロットに stock 選択を追加: `stock_of[p]` か stock別 c[p,s,j]、容量はその stock の L_s）。
  - 実装方針: `StockSpec` を複数 stock のリスト（length/kerf/available/cost?）に拡張 or 新 `StockOption`。kerf は全 stock 共通（同一saw）前提で実効幅 w_j=ℓ_j+k は不変、GCD g=gcd(w_j) を共有し各 stock 容量 W'_s=L_s//g。
  - flow_mip: stock 種ごとに arc グラフを作り、各源 source_s から出るフローに重み w_s を掛けて目的に。需要は全グラフ横断で `Σ_s Σ item-j弧フロー ≥ d_j`。
  - **入力 API は要素1で後方互換**（`stock:{length,kerf}` → `stocks:[{length,kerf,available,cost}]`、単一要素で現行同等）。
  - ※「M6 が難しくエラーになったら（次にエラーになったら）M6 は捨てて次のステップへ」とユーザー指示済み。深追いしない。
- **M7 最終レビュー（ウルトラコード）**: 正確性・性能・エッジ・UI を次元分けで敵対検証。

## M2 検証計画（ウルトラコード）— 復帰後はこの節を読んで workflow を撃つ

> M1（材料軸 arc-flow on HiGHS）は実装・13件 green 済み。M2 のゴールは
> **arc-flow の normal-patterns 縮約がサイレントに最適解を取りこぼしていないことを敵対的に証明**すること。
> ここが本設計で最も信用できていない箇所。緑になるまで M3（段取り軸）に進まない。

**実装物（ソロで先に置いてよい土台）**
- `solver/oracle.py`: CP-SAT 割当モデル（per-bin: `use[b]∈{0,1}`, `x[b,j]∈{0..}`, 容量 `Σ w_j·x[b,j] ≤ L·use[b]`,
  需要 `Σ_b x[b,j] ≥ d_j`, 対称性破り `use[b] ≥ use[b+1]`, `minimize Σ use[b]`）。小規模 ground-truth。
  ビン数上限 `B` は FFD 上界（`bounds.ffd_initial`）で与える。snake_case API（`new_int_var`/`add`/`minimize`/`solve`/`value`）。
- `solver/tests/test_oracle_crosscheck.py`: arc-flow と oracle の **使用本数（目的値）一致**を多数の小〜中インスタンスでアサート。
- `solver/tests/test_invariants.py`: kerf 不変条件の property test（`Σℓ+m·k ≤ L`, `waste ≥ 0`, 総量保存 `z·L = Σℓ充足 + Σkerf + Σwaste`）。

**ウルトラコードで敵対的にやること（workflow の fan-out 軸）**
1. **ランダム突合**: シード違いで小〜中規模インスタンス（types≲12, L≲2000, qty≲30）を大量生成し、arc-flow == oracle を回す。
   不一致が1件でも出れば縮約バグ＝最優先。各 worker が別レンジ/別シードを担当。
2. **退化・境界入力**: 需要0近傍・単一type・全同寸・`ℓ+k` がちょうど L・`ℓ+k` が L+1（PIECE_TOO_LONG 経路）・
   GCD=1 の互いに素幅（グラフ最大化）・kerf=0 と kerf 大。各ケースで例外/最適性/不変条件を確認。
3. **既知最適ベンチ**: BPPLIB（Falkenauer U120/T60, Hard28）を kerf=0 のビンパッキングとして取り込み、公表最適と一致を確認。
   データ取得不可なら、公表最適が分かる小インスタンスを埋め込みで代替（取りこぼしは log で明示）。
4. **完全性クリティック**: 「未検証の縮約経路・未生成のインスタンス族はないか」を最後に1エージェントで洗う。

**判定**: arc-flow ≠ oracle / 不変条件違反 / 既知最適との乖離 が出たら縮約 or 定式化のバグ。
再現する最小インスタンスを特定 → `arcgraph`/`flow_mip` を修正 → 全突合が緑になるまで反復。
緑なら「M2 ゲート通過」を PROGRESS に記録して M3 へ。

## 不採用と退路

- **列生成 B&P を主筋**: OR-Tools にプライサ注入APIが無く看板倒れ（提案自身が weaknesses で実体は round-up+プール固定CP-SAT と白状）。
  ただし GLOP列生成は**dev退路**として温存（将来の超大L・細粒度で材料軸が規模破綻した際の載せ替え + 独立LP下界クロスチェック）。
- **CP-SAT 割当モデルを材料軸主筋**: per-bin 割当は対称性とLP緩和の弱さで中規模 gap が閉じない。→ `oracle.py` に降格採用。
- **単一ライブラリ完結**: 各軸を証明可能な最強ツールに割り当てる価値が依存1本増を上回ると判断（ユーザー承認済み）。
- **SCIP/pyscipopt**: arc-flow/CP-SAT併用で B&P 不要。ビルド/ライセンス管理コストをソロで負う理由が消えた。
- **重み付き和パレート**: λ感度が高く非凸前線の隅を取りこぼす。整数zの狭い値域では ε制約（整数掃引）が漏れなく優れる。

## M7 最終レビュー結果（2026-06-17, ウルトラコード）

6次元（材料軸 / 段取り軸+パレート / エッジ境界 / API契約 / 性能・数値 / GUI）を並列レビューし、各 finding を
敵対 verify → 統合（run `wf_9604ac3b-767`, 28エージェント）。総 finding 21、敵対 verify 後の確定バグ 9（root cause 束ね後）。

**核の健全性**: 材料最適性と Model A 不変量（waste≥0 / 占有≤L / セグメント和=L）を **400+388 インスタンスの
クロスチェックで違反ゼロ**。arc-flow 縮約のサイレント故障は出ていない＝M2 の PASS は規模を上げても保たれる。
FAIL 判定の実体は計算の誤りでなく「JSON 境界の入力検証」「タイムアウト時の劣化処理」「廃棄量メトリクスの計上」に集中。

### 修正済み

- **bug#2 廃棄量メトリクス反転（high, 既定パレート経路で発火）** → 修正済み（`pareto.py` / `solve.py`）。
  過剰生産ピースを占有計上していたため z 増で廃棄が減る非単調が起きていた。SPEC.md:52 の定義
  `total_waste = z·L − 総需要長`（kerf・端材・過剰生産を含み z に単調）に統一。回帰 `test_pareto_waste_monotonic_spec52` 追加。
  - 注: synthesis の提案（delivered − consumed_kerf 方式）は kerf を produced 依存で差し引くため単調性を完全には
    回復しない。SPEC.md:52 の `z·L − 総需要長` が SSOT かつ厳密単調なのでそちらを採用した。

### 未修正（ユーザー判断 2026-06-17: 既定GUI正常系では発火しない off-default パスのため文書化のみ）

いずれも「外部から JSON API に異常値を投げる」「非整数/非有限 float を渡す」「不正オプションを渡す」経路で、
既定 GUI 操作（整数入力・time_limit=null 無制限・max_extra_bars=3）では到達しない。将来直すときの地図として残す。

| # | sev | 症状 | 所在 | トリガ |
|---|---|---|---|---|
| 1 | high | time_limit 到達で incumbent 無しのとき `round(+inf)` → OverflowError が api/CLI/HTTP を未捕捉貫通 | flow_mip.py:92 | `time_limit_sec=0`（HiGHS では 0=即timeout） |
| 3 | high | 非整数 float の黙示 floor → kerf 切り捨てで PIECE_TOO_LONG をすり抜け「入らない切り方」を waste=0 で受理 | api.py parse_problem の int() | `kerf=10.9` 等 |
| 4 | high | 不正オプションが生例外で HTTP500/CLI トレースバック（契約 {status:ERROR} 違反） | api.py:131-135（try外） | `max_extra_bars='abc'`/None, `time_limit_sec='x'` |
| 5 | high | 負の max_extra_bars で status=OK・空フロント・idx=-1 → consumer IndexError | pareto.py:45,61-64 / api.py:132 | `max_extra_bars=-1` |
| 6 | med | float ±inf が except をすり抜け OverflowError 貫通（NaN は偶然捕捉） | api.py:33 | `kerf=Infinity` |
| 7 | med | 段取り軸タイムアウト時、材料バッジが「gap 0.0%（上界）」と自己矛盾表示し証明済み緑を握りつぶす | OptimalityBadge.tsx:5 / pareto.py:22,26 | 有限 time_limit + 段取り timeout |
| 8 | low | proven_optimal の二重裏取り leg(b)（z_int≥⌈z_LP⌉）を計算するが enforce しない（実答は常に正しく防御網のみ欠落） | solve.py:35 | （発火せず） |
| 9 | low | 不正/大小文字違いの mode を黙って pareto 扱い。doc 記載の 'setup' モードが独立挙動として存在しない | api.py:131 / solve.py:66 | doc-vs-code 不整合 |

一括修正するなら #3〜#6 は同一 family（境界の未検証/不正 coercion）で api.py の数十行に集約でき、契約
（必ず {status:ERROR} 包絡・CLI/HTTP 振る舞い一致）を回復できる。#1 は flow_mip の round 前 status 分岐＋isfinite ガード。
#7 はフロント判定順を proven_optimal 優先に並べ替え。#8/#9 は防御網/doc 整合で任意。

### 本質的限界（修正不要・設計スコープ）

- arc-flow グラフは擬多項式構築のため L 大＋互いに素幅で item_arcs が二次膨張（実測 L=20000・coprime で ≈4.3M / 0.64s）。
  中小規模スコープ（L=数千mm）内では問題なし。L が万単位に増えるとメモリ/構築時間が支配的になる。
- 1D-CSP は NP 困難で大規模では time_limit 到達が原理的に起こりうる（到達時のクラッシュは限界でなく #1 の実装欠陥）。
  証明付き最適は中小規模前提、大規模では timed_out 上界解になりうる。
- INFEASIBLE は単一原材料長では到達不能（ℓ+k≤L なら必ず自分のビンに入る／超えれば PIECE_TOO_LONG）。
  M6 複数長で初めて producer が現れる前方足場＝現状は予約コード。
- 過剰生産（Σ≥d）自体は M2 オラクル相互チェックの構造要件で意図的（#2 のメトリクス計上ミスとは別問題）。

### 残るカバレッジギャップ（M7 でも未踏）

- HTTP 層の実トラフィック挙動（FastAPI RequestValidationError ハンドラ有無・並行リクエスト・HF Spaces 環境固有のタイムアウト/プロキシ）。
- 実業務想定の最大規模（多種長×大需要×L大）での解品質・solve 時間・メモリ・time_limit 上界解の gap 実分布。
- フロント実ブラウザの全ユーザーフロー E2E（スライダ→再solve→比較トグル→再描画）と空フロント/エラー応答受信時の UI 挙動。
- CLI 入力堅牢性（標準入力ストリーミング・巨大ペイロード・部分 JSON・文字エンコーディング境界）。
- 性能次元の review エージェントは socket 切れで 1 個脱落（28中1）。上記の性能関連は他次元＋統合が部分的に拾ったが、最大規模の実測だけは未実施。

## 段取り軸の計算量天井とロバスト化（2026-06-18, Wikipedia古典例で検出）

Wikipedia "Cutting stock problem" 製紙ロール例（L=5600, k=0, 13品目219本, 既知最適73本/0.401%/最少種類10）で検証:

- **材料軸は満点**（73本/廃棄1640/0.401%/proven_optimal）。確定。
- **設定モデルBは「中小規模」でも破綻**。出荷コードは `R = bars`（=73スロット, 設計の「R=types初期値」からのドリフト）。
  73スロット×非凸整数積で CP-SAT が重すぎ、90〜300秒でも実行可能解を返せず `status=UNKNOWN` → `pareto.py` がその点を黙ってスキップ。
  結果、出力が**非再現（13が出る/空が揺れる）**。`num_workers=8`＋時間切れの非決定性が拍車をかける。
  （※過去に「13をsetup_proven=Trueで誤証明」と記録されたが、実コードは嘘の証明をしない。あれは作話だった。）

**ロバスト化（実装済み）** — `setup_mip.py`/`pareto.py`:
1. warm-start: 材料解パターンを初期可行点として `add_hint` 注入（UNKNOWN/空を封じる）。
2. R縮約: `R = len(seed_patterns) = P_mat`。最適 `P ≤ P_mat` ゆえ最適解を切り落とさない＝**証明を保ったままモデルを縮小**（設計の R=types 意図に復帰）。
3. フォールバック anchor: ソルバが解なし/種より悪い時は材料解を採用、点を絶対に落とさない（status=FEASIBLE, proven=False で正直）。
- 効果: 出力が**完全再現**・空にならない・z=73 の P が 13→12 に改善・前線が本物に（12/8）。テスト55 green維持。

**残る天井**: z=73 の P は **12 で頭打ち, proven立たず**（90/300秒で不変）。既知最適10には未達。
→ 設計(本節「段取り軸」フォールバック記述)の「中小では候補プール退避は基本発動しない見込み」は**棄却**。

**B 実装済み（2026-06-18）= 候補プール選択MIPを主経路化**（`setup_mip.py`）:
maximal パターンを全列挙（`_enumerate_maximal_patterns`）→ 使用本数 x_q・使用フラグ y_q の線形MIP
（`Σx==bars`, `Σ a·x ≥ d`, `min Σy`, `num_workers=1` で決定論）。非凸積が消え tractable。
maximal に限定しても最適性を失わない（非maximalは含む maximalへ同一本数で置換可・需要≥・本数不変・種類非増）ため、
**全列挙が尽きれば真の最小に一致＝proven 正当**。列挙が cap(5万) 超なら config-B へ退避（その時のみ上界・proven=False）。
- 結果: **z=73 で P=10 を proven 到達**（config-Bの12止まりを突破, Wikipedia既知最小10に一致）、z=74 で P=8 proven。バイト完全再現。
- 回帰: `solver/tests/test_benchmark.py`（maximal列挙の単体 + Wikipedia既知最適突き合わせ, `slow` marker で隔離）。既定スイート57 green。
- 教訓: 既知最適ベンチマークとの突き合わせは、不変条件チェックが見逃す「制約は満たすが最適でない」型を捕える。M7はこれを欠いていた。

## 先送り事項（既定で進め、見えた段階で再判断）

- パレート掃引幅 `B`: 既定 **3**（GUI可変）。中小規模なら拡げても安価。
- 複数原材料長の既定材料目的（M6で確定）。原材料ごとの単価/在庫上限を入力に持たせるかも M6 で判断。
