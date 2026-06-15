# ソルバ核 設計（確定）

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

物理ビンでなく**パターンスロット**を変数化（候補プール非依存＝真の最小を証明可能）。
- `s_used[p] ∈ {0,1}`、`c[p,j] ∈ [0, L//w_j]`（パターン内容を自由変数化）、`n[p] ∈ [0, Nb]`。
- 妥当パターン: `Σ_j w_j·c[p,j] ≤ L`。リンク: `s_used[p] ≤ n[p] ≤ Nb·s_used[p]`。
- 本数バジェット: `Σ_p n[p] == Nb`（= パレート制御変数）。
- 需要: `z[p,j] = AddMultiplicationEquality(n[p], c[p,j])`; `Σ_p z[p,j] ≥ d_j`。
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
- **二重裏取り**: 材料軸は (a) `mip_gap==0.0`、(b) LP緩和を別途解き `z_int ≥ ⌈z_LP⌉` を確認。両者一致で round-up property
  成立＝ソルバ自己申告に依存しない第2証拠。段取り軸は `status==OPTIMAL` かつ `BestObjectiveBound==ObjectiveValue`。
- **Optimality データ**（全解に必ず添付, ネスト dataclass）: `Optimality(mip_gap, lp_lower_bound, proven_optimal=(gap==0 and lb==obj), setup_proven, status, timed_out)`。
  `OPTIMAL` を名乗るのは `gap=0 かつ LB=解値` のときだけ。
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

- **M0 セットアップ（ソロ）**: `uv add highspy ortools`。`flow_mip`/`setup_mip` に10行スモークテストを書き、
  `highspy.addVariable`/`getInfo().mip_gap`・`cp_model.AddMultiplicationEquality` の API 実在を**本環境で裏取り**
  （各審査の「実機検証済み」主張は別サンドボックスのもの。検証プロトコル順守）。`models.py` の dataclass 定義。
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
  ※複数長では「本数最小 / 廃棄最小 / コスト最小」が分離する（数学的事実）。**既定の材料目的は M6 着手時に別途確定**（要ユーザー判断）。
  data model は `stock_length` + 将来の cost/available を見越し済み。M1 のテストが要素1退化で緑のままを回帰保証。
- **M7 最終レビュー（ウルトラコード）**: 正確性・性能・エッジ・UI を次元分けで敵対検証。

## 不採用と退路

- **列生成 B&P を主筋**: OR-Tools にプライサ注入APIが無く看板倒れ（提案自身が weaknesses で実体は round-up+プール固定CP-SAT と白状）。
  ただし GLOP列生成は**dev退路**として温存（将来の超大L・細粒度で材料軸が規模破綻した際の載せ替え + 独立LP下界クロスチェック）。
- **CP-SAT 割当モデルを材料軸主筋**: per-bin 割当は対称性とLP緩和の弱さで中規模 gap が閉じない。→ `oracle.py` に降格採用。
- **単一ライブラリ完結**: 各軸を証明可能な最強ツールに割り当てる価値が依存1本増を上回ると判断（ユーザー承認済み）。
- **SCIP/pyscipopt**: arc-flow/CP-SAT併用で B&P 不要。ビルド/ライセンス管理コストをソロで負う理由が消えた。
- **重み付き和パレート**: λ感度が高く非凸前線の隅を取りこぼす。整数zの狭い値域では ε制約（整数掃引）が漏れなく優れる。

## 先送り事項（既定で進め、見えた段階で再判断）

- パレート掃引幅 `B`: 既定 **3**（GUI可変）。中小規模なら拡げても安価。
- 複数原材料長の既定材料目的（M6で確定）。原材料ごとの単価/在庫上限を入力に持たせるかも M6 で判断。
