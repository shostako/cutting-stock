"""段取り軸: ちょうど bars 本で需要を満たす最小パターン種類数 P を求める.

2段構え:
- 主経路 = 候補プール選択MIP（`min_pattern_types`）: maximal パターンを全列挙し、各パターンの
  使用本数 x_q（整数）と使用フラグ y_q の線形MIP（Σx==bars, Σ a·x ≥ d, min Σy）で解く。
  非凸積を持たず tractable。maximal 全列挙が尽きれば、その最小は全パターンに対する真の最小に
  一致するため proven=True が正当（任意の非maximalパターンは、それを含む maximal パターンへ
  同一本数で置換でき、需要 ≥・本数不変・種類数非増のため最適性を失わない）。
- フォールバック = config-B スロット定式化（`_solve_configb`）: maximal 列挙が cap を超える大規模向け。
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


def _enumerate_maximal_patterns(widths: list[int], L: int, cap: int) -> list[tuple[int, ...]] | None:
    """Σ widths[j]·count[j] ≤ L かつ maximal（最小幅すら追加で入らない）な count ベクトルを全列挙.

    maximal に限定しても ≥需要 のパターン種類最小化では最適性を失わない（非maximalパターンは
    それを含む maximal パターンへ同一本数で置換でき、需要 ≥・本数不変・種類数非増）.
    列挙数が cap を超えたら None（列挙不能 = 大規模 → config-B フォールバックへ）.
    """
    n = len(widths)
    min_w = min(widths)
    out: list[tuple[int, ...]] = []
    counts = [0] * n

    def dfs(i: int, used: int) -> bool:               # 戻り False = cap 超過で打ち切り
        if i == n:
            if L - used < min_w:                      # これ以上どのピースも入らない = maximal
                out.append(tuple(counts))
                if len(out) > cap:
                    return False
            return True
        wi = widths[i]
        for cj in range((L - used) // wi, -1, -1):
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
    """ちょうど bars 本で需要を満たす最小パターン種類数 P を求める（主経路 = 候補プール選択MIP）.

    maximal パターンを全列挙し、使用本数 x_q・使用フラグ y_q の線形MIP（Σx==bars, Σ a·x ≥ d,
    min Σy）で解く。プールが尽きれば真の最小に一致＝proven 正当。列挙不能なら config-B へ退避.
    seed_patterns はフォールバック経路へ素通しするだけ（プール経路は warm-start 不要）.
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

    pool = _enumerate_maximal_patterns(widths, L, _POOL_CAP)
    if pool is None:                                  # 列挙不能な大規模 → スロット定式化へ
        return _solve_configb(problem, bars, seed_patterns=seed_patterns, time_limit=time_limit)

    model = cp_model.CpModel()
    Q = len(pool)
    x = [model.new_int_var(0, bars, f"x_{q}") for q in range(Q)]
    y = [model.new_bool_var(f"y_{q}") for q in range(Q)]
    for q in range(Q):
        model.add(x[q] <= bars * y[q])                # y_q=0 ⟹ x_q=0（未使用パターン）
    model.add(sum(x) == bars)                          # ちょうど bars 本
    for j in range(n_types):
        model.add(sum(pool[q][j] * x[q] for q in range(Q)) >= demands[j])   # 需要充足（≥）
    model.minimize(sum(y))                             # 異種パターン数の最小化

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
    caps = [L // widths[j] for j in range(n_types)]   # 1本に入る各typeの最大本数

    # warm-start 種: 材料解パターンを「ちょうど bars 本」へ調整（余り本数は先頭パターンに吸収＝過剰生産→廃棄）.
    seed: list[tuple[Pattern, int]] = []
    if seed_patterns:
        runs = [p.run_count for p in seed_patterns]
        extra = bars - sum(runs)
        if extra >= 0 and runs:
            adj = list(runs)
            adj[0] += extra
            seed = [(pat, run) for pat, run in zip(seed_patterns, adj) if run > 0]

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
        model.add(sum(produced) >= demands[j])

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
