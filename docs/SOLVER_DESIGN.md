# ソルバ核 設計（SSOT — 現行）

> 本ドキュメントは**現行実装**の SSOT。`docs/SPEC.md`（問題仕様・Model A）を前提とする。
> 設計に至る経緯（旧・二軸パレート設計、段取り軸の定式化変遷、M0-M7 マイルストン履歴）は
> `docs/history/` を参照。ここには「今どう動いているか」だけを書く。

## 全体像: 辞書式2段最適化（単一解）

`solve(problem)` は以下を順に解き、**単一解**を返す。パレート前線・トレードオフは提供しない。

1. **① 使用本数最小化**（材料軸）: arc-flow MIP on HiGHS。gap=0 厳密証明。
   単一原材料長なら使用本数最小 = 廃棄量最小（廃棄 `= z·L − 総需要長` は z の単調関数）。
2. **② 切り方（パターン種類数）最小化**（段取り軸）: ①の最少本数 z* を固定したまま、
   CP-SAT 候補プール選択MIP で異種パターン数 P を最小化。証明付き。

**需要は両段とも `==` で締める（2026-07-02 確定）**: 過剰生産＝切らなくてよいピースを一切作らない。
余剰は未カットの端材として残す。廃棄量の定義（`z·L − 総需要長`）は不変で、余計なカット工数と
「過剰生産」表示だけが消える。z* も不変（≥ の任意解は余剰ピースを loss 弧＝未カット端材に置換できる）。

## アーキテクチャ（I/O 完全分離・純関数核・依存局所化）

```
solver/
  models.py     # 純dataclass(frozen)・依存ゼロ。StockSpec/DemandItem/Problem/Pattern/Solution/Optimality
  normalize.py  # 重複長マージ・整数化・GCD縮約（純関数, 冪等）
  bounds.py     # continuous_lower_bound / validate_input / ffd_initial
  arcgraph.py   # arc-flowグラフ構築（normal patterns / canonical order）。ソルバ非依存・純関数
  flow_mip.py   # ★highspy依存。材料最適MIP + LP独立下界
  decompose.py  # フロー分解 → Pattern列（純関数）
  setup_mip.py  # ★ortools(CP-SAT)依存。候補プール選択MIP（主経路）+ config-B（大規模フォールバック）
  oracle.py     # ★ortools(CP-SAT)依存。割当モデル直接解（小規模ground-truth, CIクロスチェック）
  verify.py     # oracle との突合ユーティリティ
  solve.py      # 公開エントリ solve(problem) -> Solution（唯一の外部ロジック入口）
  api.py        # 唯一のJSON境界。dict <-> dataclass 変換 + segments前計算。ソルバ非依存
  cli.py        # stdin/stdout 薄ラッパ
  http.py       # FastAPI 薄ラッパ（/solve /validate /healthz + web/dist 配信）
```

- `solve.py` 以下は純Python + (highspy/ortools) のみ。print/file/HTTP なし＝冪等・副作用ゼロ。
- ソルバ依存は `flow_mip` / `setup_mip` / `oracle` の3ファイルに閉じる。
- CLI と HTTP は同じ `api.solve_from_dict` を呼ぶ＝振る舞い一致保証。

### 想定規模・方針（ユーザー確定 2026-06-16）

| 論点 | 決定 |
|---|---|
| ライブラリ | `highspy`（材料軸）+ `ortools`/CP-SAT（段取り軸+オラクル）の2本立て |
| 問題規模 | 中小（distinct長 ≲20, 総本数 ≲数百, mm単位・L=数千mm）。列生成への退路は仕込まない |
| 最適性 | 常に gap=0 まで粘る。`time_limit` は安全天井。未達時は gap を正直表示し OPTIMAL を詐称しない |

カット代は Model A（`docs/SPEC.md`）: 実効幅 `w_i = ℓ_i + k`、占有長制約 `Σℓ_j + m·k ≤ L`、容量 `L`。

## ① 材料軸: Arc-flow MIP on HiGHS

1. **正規化**（`normalize.py`）: 重複長マージ → 実効幅降順の canonical order → GCD `g` で縮約（`L' = L/g`）。
   `ℓ_i + k > L` は MIP に渡す前に `PIECE_TOO_LONG` で弾く。
2. **グラフ**（`arcgraph.py`）: de Carvalho の normal patterns。item弧 `d → d+w_i` は
   「items {0..i-1} で到達した位置」からのみ張り、経路上 item index 非減少＝各パターンが 0→L' 経路に 1:1。
   loss弧は全頂点 → L'（任意の部分multisetパターンが経路として表現可能＝需要 == の可行性の根拠）。
3. **MIP**（`flow_mip.py`）: フロー保存 + 需要充足 `Σ item弧フロー == d_i`。目的 = vertex0 から出るフロー（使用本数）。
4. **分解**（`decompose.py`）: フロー分解 → 0→L' 経路 = 原材料1本のカットパターン。

## ② 段取り軸: 候補プール選択MIP（主経路）

`min_pattern_types(problem, bars=z*, seed_patterns=材料解)`:

- **全有効パターンを列挙**（`_enumerate_patterns`: `Σw ≤ L`, 非空）。== では maximal 限定が使えない
  （maximal 置換は生産を増やし == を壊す）が、プール＝全パターンゆえ「選択MIPの最小 = 真の最小」で proven が正当。
- **支配的枝刈り**（2026-07-02）: `count[j] > d_j` のパターンは1本使った時点で過剰生産確定＝使用本数0しか
  許されないため列挙から除外（証明無傷）。使用本数上限も `x_q ≤ min_j ⌊d_j / a_qj⌋` に締める。
- **MIP**: `x_q ∈ [0, x_ub_q]`（使用本数）, `y_q ∈ {0,1}`（使用フラグ）。
  `Σx == bars`, `Σ_q a_qj·x_q == d_j`, `x_q ≤ x_ub_q·y_q`, `min Σy`。
  `num_workers=1, random_seed=0` で完全決定論（同点解の揺れも封じる）。
- 材料解（== を満たす）を warm-start ヒント注入。
- 列挙が cap（`_POOL_CAP`=5万）超なら **config-B フォールバック**へ: スロット定式化
  （パターン内容を自由変数化、`add_multiplication_equality` の非凸積）+ warm-start/R縮約/anchor。
  中規模でも最適到達を保証できないため、あくまで大規模用の退避。点は絶対に落とさない
  （ソルバが解なし/種より悪い時は材料解 anchor 採用, proven=False で正直）。

`solve()` は第2段が時間内（既定 `_SETUP_TIME_LIMIT`=30s）に解を返せなければ材料分解にフォールバックし
`patterns_min_proven=False`。本数の `proven_optimal` は常に保たれる。

## 最適性・検証・不変条件

- **二重裏取り（材料軸）**: (a) `status==Optimal かつ mip_gap < 1e-9`（float 許容誤差 `_GAP_TOL`。
  厳密比較は HiGHS の machine-epsilon 残差で偽陰性を出す — M2 の教訓）、(b) LP緩和の独立下界 `z ≥ ⌈z_LP⌉`。
- **段取り軸**: `status==OPTIMAL かつ best_objective_bound == objective_value` のときだけ proven=True。
- **オラクル**（`oracle.py`）: CP-SAT 割当モデルの独立 ground-truth と bars_used 一致を CI で突合
  （arc-flow 縮約のサイレント最適解取りこぼしを潰す保険。M2 で ~2万件突合、取りこぼしゼロ実証済み）。
- **既知最適ベンチマーク**（`test_benchmark.py`, `-m slow`): Wikipedia 製紙ロール例
  （L=5600, 13品目219本）で 73本 / 廃棄1640 / 0.401% / **切り方10通り**、需要ちょうど、両方証明付き。
  不変条件テストが見逃す「制約は満たすが最適でない」型を捕える（M7 の教訓）。
- **kerf不変条件**: 全パターンで `Σℓ_j + m·k ≤ L`, `waste ≥ 0`, 総量保存 `z·L = Σℓ + Σkerf + Σwaste`。

## データモデル・API

- `Pattern`: `cuts`（物理カット順）+ `item_counts`（length→本数）両持ち。`stock_length` / `waste` / `run_count`。
- `Solution`: `bars_used`, `patterns`, `total_waste`, `waste_ratio`, `num_pattern_types`, `optimality: Optimality`。
- `Optimality`: `status, mip_gap, lp_lower_bound, proven_optimal, patterns_min_proven, timed_out`。

入力 JSON: `{"stock": {"length", "kerf"}, "demand": [{"length", "qty", "label"}], "options": {"time_limit_sec"}}`
出力 JSON: `{"status": "OK", "validation": [], "input_echo", "lower_bound_bins", "solution", "meta"}`
- `solution.patterns[].segments[]`: `{kind: piece|kerf|waste, offset, length, item_length, label}` を API 側で前計算。
  **segments の length 合計 = stock_length が常に成立**（Model A 整合不変量）。
- エラー: `{"status":"ERROR","error":{"code":"INFEASIBLE|PIECE_TOO_LONG|INVALID_INPUT","message":...}}`。/solve は常に HTTP200。

## 変更履歴（詳細は docs/history/）

- **2026-06-16**: 設計確定（ultracode 3案コンペ）・M0-M2 実装。M2 敵対検証で報告層の float 厳密比較バグ発見→修正。
- **2026-06-18**: 段取り軸 config-B の非再現・空出力を実測で確定 → ロバスト化（warm-start/R縮約/anchor）の上、
  候補プール選択MIP を主経路化（Wikipedia P=10 proven 到達）。`docs/history/RESOLUTION-2026-06-18.md`。
- **2026-06-20**: 二軸パレート撤回、辞書式2段（単一解）に再構成。`pareto.py` 削除（旧実装 git `f66f8d2`）。
- **2026-07-02**: 需要制約を両段 `==` に統一（過剰生産の廃止）。プールを全有効パターン列挙に拡大 + 需要による
  支配的枝刈り。Wikipedia 73本/P=10 proven 維持を回帰で固定。
