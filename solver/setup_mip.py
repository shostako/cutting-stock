"""段取り軸: ちょうど bars 本で需要を「ちょうど」満たす最小パターン種類数 P を求める.

需要は == で締める（過剰生産＝切らなくてよいピースを一切作らない）. 廃棄は未カットの端材として
残す. このため候補は maximal に限定できず（maximal 置換は生産を増やし == を壊す）、
有効パターン（Σw ≤ L, 非空）を全列挙する.

2段構え:
- 主経路 = 候補プール選択MIP（`min_pattern_types`）: 有効パターンを全列挙し、各パターンの
  使用本数 x_q（整数）と使用フラグ y_q の線形MIP（Σx==bars, Σ a·x == d, min Σy）で解く。
  非凸積を持たず tractable。プール＝全パターンなので、その最小は真の最小＝proven=True が正当。
- フォールバック = config-B スロット定式化（`_solve_configb`）: 全列挙が cap を超える大規模向け。
  パターン内容を自由変数化し n[p]·c[p,j] の非凸積で解く。warm-start/R縮約/anchor で頑健化済みだが、
  中規模でも最適到達を保証できない（2026-06-18 Wikipedia検証で判明, docs/SOLVER_DESIGN.md）。
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from solver.models import Pattern, Problem

_STATUS_NAMES = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


@dataclass(frozen=True)
class SetupResult:
    num_patterns: int                  # P（このバジェット下の最小異種パターン数）
    patterns: tuple[Pattern, ...]
    status: str
    proven: bool                       # P が最小であることを CP-SAT が証明したか
    bars: int                          # Nb（本数バジェット）


def _patterns_from_seed(L: int, seed: list[tuple[Pattern, int]]) -> list[Pattern]:
    """warm-start 種（パターン, 本数）を、同一内容を併合した Pattern 群に正規化する."""
    by_content: dict[tuple, Pattern] = {}
    for pat, run in seed:
        if run <= 0:
            continue
        if pat.item_counts in by_content:
            prev = by_content[pat.item_counts]
            by_content[pat.item_counts] = Pattern(L, prev.cuts, prev.item_counts, prev.run_count + run)
        else:
            by_content[pat.item_counts] = Pattern(L, pat.cuts, pat.item_counts, run)
    return sorted(by_content.values(), key=lambda p: (-p.run_count, p.item_counts))


_POOL_CAP = 50_000


def _enumerate_patterns(
    widths: list[int], L: int, cap: int, demands: list[int] | None = None
) -> list[tuple[int, ...]] | None:
    """Σ widths[j]·count[j] ≤ L の非空な count ベクトル（有効パターン）を全列挙.

    需要を == で締めるため maximal に限定できない（maximal 置換は生産を増やして == を壊す）.
    プール＝全パターンなら、選択MIPの最小は真の最小＝proven が正当.

    demands を与えると **支配的枝刈り**: `count[j] > d_j` のパターンは1本使った時点で
    過剰生産が確定し == 制約下で使用本数 0 しか許されないため、列挙から安全に除外できる
    （最適性・証明は無傷）. 列挙空間が「棒に入る数」から「需要数」上限に締まり、桁で縮む.
    列挙数が cap を超えたら None（列挙不能 = 大規模 → config-B フォールバックへ）.
    """
    n = len(widths)
    out: list[tuple[int, ...]] = []
    counts = [0] * n

    def dfs(i: int, used: int) -> bool:               # 戻り False = cap 超過で打ち切り
        if i == n:
            if used > 0:                              # 空パターン（何も切らない）は除外
                out.append(tuple(counts))
                if len(out) > cap:
                    return False
            return True
        wi = widths[i]
        hi = (L - used) // wi
        if demands is not None:
            hi = min(hi, demands[i])                  # 支配的枝刈り: 需要超のカウントは使用不能
        for cj in range(hi, -1, -1):
            counts[i] = cj
            if not dfs(i + 1, used + cj * wi):
                counts[i] = 0
                return False
        counts[i] = 0
        return True

    return out if dfs(0, 0) else None


def min_pattern_types(
    problem: Problem,
    bars: int,
    *,
    seed_patterns: tuple[Pattern, ...] | None = None,
    time_limit: float | None = None,
) -> SetupResult:
    """ちょうど bars 本で需要を「ちょうど」満たす最小パターン種類数 P を求める（主経路 = 候補プール選択MIP）.

    有効パターンを全列挙し、使用本数 x_q・使用フラグ y_q の線形MIP（Σx==bars, Σ a·x == d,
    min Σy）で解く。プール＝全パターンなので最小は真の最小＝proven 正当。列挙不能なら config-B へ退避.
    seed_patterns は warm-start ヒント（材料解は == を満たすので常に可行）兼フォールバック素通し.
    """
    L = problem.stock.length
    k = problem.stock.kerf

    merged: dict[int, int] = {}
    for it in problem.demand:
        merged[it.length] = merged.get(it.length, 0) + it.qty
    lengths = sorted(merged.keys(), reverse=True)
    demands = [merged[length] for length in lengths]
    widths = [length + k for length in lengths]
    n_types = len(lengths)

    pool = _enumerate_patterns(widths, L, _POOL_CAP, demands)
    if pool is None:                                  # 列挙不能な大規模 → スロット定式化へ
        return _solve_configb(problem, bars, seed_patterns=seed_patterns, time_limit=time_limit)

    model = cp_model.CpModel()
    Q = len(pool)
    # x_q の上限は「どの品目も需要を超えない本数」= min_j ⌊d_j / a_qj⌋（== 制約から従う正当な締め付け）
    x_ub = [
        min([bars] + [demands[j] // pool[q][j] for j in range(n_types) if pool[q][j] > 0])
        for q in range(Q)
    ]
    x = [model.new_int_var(0, x_ub[q], f"x_{q}") for q in range(Q)]
    y = [model.new_bool_var(f"y_{q}") for q in range(Q)]
    for q in range(Q):
        model.add(x[q] <= x_ub[q] * y[q])             # y_q=0 ⟹ x_q=0（未使用パターン）
    model.add(sum(x) == bars)                          # ちょうど bars 本
    for j in range(n_types):
        model.add(sum(pool[q][j] * x[q] for q in range(Q)) == demands[j])   # 需要「ちょうど」充足（過剰生産なし）
    model.minimize(sum(y))                             # 異種パターン数の最小化

    if seed_patterns:                                 # 材料解（== を満たす）を warm-start ヒント注入
        pool_index = {counts: q for q, counts in enumerate(pool)}
        seed_runs: dict[int, int] = {}
        for pat in seed_patterns:
            by_len = dict(pat.item_counts)
            counts = tuple(by_len.get(length, 0) for length in lengths)
            q = pool_index.get(counts)
            if q is None:                             # プールに無い（理論上は起きない）→ ヒント断念
                seed_runs = {}
                break
            seed_runs[q] = seed_runs.get(q, 0) + pat.run_count
        if seed_runs and sum(seed_runs.values()) == bars:
            for q, run in seed_runs.items():
                model.add_hint(x[q], run)
                model.add_hint(y[q], 1)

    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_workers = 1                 # 単一ワーカで完全決定論（同点解の揺れも封じる）
    solver.parameters.random_seed = 0
    status = solver.solve(model)
    status_name = _STATUS_NAMES.get(status, str(status))
    proven = status == cp_model.OPTIMAL and solver.best_objective_bound == solver.objective_value

    by_content: dict[tuple, Pattern] = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for q in range(Q):
            run = round(solver.value(x[q]))
            if run <= 0:
                continue
            counts = pool[q]
            item_counts = tuple(sorted((lengths[j], counts[j]) for j in range(n_types) if counts[j] > 0))
            cuts = tuple(sorted(
                (lengths[j] for j in range(n_types) for _ in range(counts[j])), reverse=True
            ))
            by_content[item_counts] = Pattern(L, cuts, item_counts, run)

    patterns = sorted(by_content.values(), key=lambda p: (-p.run_count, p.item_counts))

    if not patterns:                                  # 異常時のみ config-B へ退避（点を落とさない）
        return _solve_configb(problem, bars, seed_patterns=seed_patterns, time_limit=time_limit)

    return SetupResult(
        num_patterns=len(patterns),
        patterns=tuple(patterns),
        status=status_name,
        proven=proven,
        bars=bars,
    )


def _solve_configb(
    problem: Problem,
    bars: int,
    *,
    seed_patterns: tuple[Pattern, ...] | None = None,
    time_limit: float | None = None,
) -> SetupResult:
    """フォールバック: スロット定式化（config-B）+ warm-start/R縮約/anchor.

    seed_patterns（材料軸の解パターン）を与えると warm-start する:
    - スロット上限 R を材料解の種類数 P_mat に縮約（最適 P ≤ P_mat なので証明は保たれる）.
    - 材料解を初期可行点として CP-SAT にヒント注入（UNKNOWN/空出力を封じる）.
    - ソルバが解を返せなくても材料解を anchor として採用し、点を絶対に落とさない.
    """
    L = problem.stock.length
    k = problem.stock.kerf

    merged: dict[int, int] = {}
    for it in problem.demand:
        merged[it.length] = merged.get(it.length, 0) + it.qty
    lengths = sorted(merged.keys(), reverse=True)     # canonical（長さ降順）
    demands = [merged[length] for length in lengths]
    widths = [length + k for length in lengths]
    n_types = len(lengths)
    caps = [min(L // widths[j], demands[j]) for j in range(n_types)]   # 1本に入る最大本数 ∧ 需要（== 下では需要超は使用不能）

    # warm-start 種: 材料解パターン（== を満たす）をそのまま使う. 本数が合わない種は == を壊すため不採用.
    seed: list[tuple[Pattern, int]] = []
    if seed_patterns and sum(p.run_count for p in seed_patterns) == bars:
        seed = [(pat, pat.run_count) for pat in seed_patterns if pat.run_count > 0]

    R = len(seed) if seed else bars                   # スロット上限（P ≤ 既知可行解の種類数, なければ bars）
    model = cp_model.CpModel()
    s_used = [model.new_bool_var(f"s_{p}") for p in range(R)]
    c = [[model.new_int_var(0, caps[j], f"c_{p}_{j}") for j in range(n_types)] for p in range(R)]
    n = [model.new_int_var(0, bars, f"n_{p}") for p in range(R)]

    for p in range(R):
        model.add(sum(widths[j] * c[p][j] for j in range(n_types)) <= L)   # 妥当パターン（空も許容）
        model.add(s_used[p] <= n[p])
        model.add(n[p] <= bars * s_used[p])
    model.add(sum(n) == bars)

    for j in range(n_types):
        produced = []
        for p in range(R):
            z_pj = model.new_int_var(0, bars * caps[j], f"z_{p}_{j}")
            model.add_multiplication_equality(z_pj, [n[p], c[p][j]])
            produced.append(z_pj)
        model.add(sum(produced) == demands[j])        # 需要「ちょうど」充足（過剰生産なし）

    for p in range(R - 1):
        model.add(s_used[p] >= s_used[p + 1])         # 対称性破り
    model.minimize(sum(s_used))

    if seed:                                          # 材料解を初期可行点としてヒント注入
        for p, (pat, run) in enumerate(seed):
            counts = dict(pat.item_counts)
            model.add_hint(s_used[p], 1)
            model.add_hint(n[p], run)
            for j, length in enumerate(lengths):
                model.add_hint(c[p][j], counts.get(length, 0))

    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_workers = 8
    status = solver.solve(model)
    status_name = _STATUS_NAMES.get(status, str(status))
    proven = status == cp_model.OPTIMAL and solver.best_objective_bound == solver.objective_value

    by_content: dict[tuple, Pattern] = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for p in range(R):
            run = round(solver.value(n[p]))
            if run <= 0:
                continue
            counts: dict[int, int] = {}
            for j in range(n_types):
                cj = round(solver.value(c[p][j]))
                if cj > 0:
                    counts[lengths[j]] = cj
            if not counts:
                continue                              # 空パターンは捨てる（最適では現れない）
            item_counts = tuple(sorted(counts.items()))
            cuts = tuple(sorted((length for length, cnt in item_counts for _ in range(cnt)), reverse=True))
            if item_counts in by_content:             # 同一内容は併合（保険）
                prev = by_content[item_counts]
                by_content[item_counts] = Pattern(L, prev.cuts, item_counts, prev.run_count + run)
            else:
                by_content[item_counts] = Pattern(L, cuts, item_counts, run)

    patterns = sorted(by_content.values(), key=lambda p: (-p.run_count, p.item_counts))

    # フォールバック: ソルバが何も返さない / 種より悪い場合は材料解 anchor を採用（点を絶対に落とさない）.
    if seed and (not patterns or len(patterns) > len(seed)):
        patterns = _patterns_from_seed(L, seed)
        status_name = "FEASIBLE"
        proven = False

    return SetupResult(
        num_patterns=len(patterns),
        patterns=tuple(patterns),
        status=status_name,
        proven=proven,
        bars=bars,
    )
