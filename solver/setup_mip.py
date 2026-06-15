"""段取り軸: パターン種類数の最小化 = CP-SAT 設定モデルB.

物理ビンでなく「パターンスロット」を変数化する（候補プール非依存＝種類数の真の最小を証明できる）。
固定の本数バジェット Nb（= 使用本数 z）の下で、需要を満たす最小の異なるパターン種類数 P を求める.

スロット p:
  s_used[p]∈{0,1}, c[p,j]∈[0, L//w_j]（パターン内容を自由変数化）, n[p]∈[0,Nb]（このパターンを使う本数）.
  妥当性 Σ_j w_j·c[p,j] ≤ L / リンク s_used[p] ≤ n[p] ≤ Nb·s_used[p] / 本数 Σ_p n[p] == Nb /
  需要 z[p,j]=n[p]·c[p,j], Σ_p z[p,j] ≥ d_j / 対称性破り s_used[p] ≥ s_used[p+1] / min Σ s_used.
同一内容スロットは目的最小化が1スロットに併合するため、Σ s_used = 真の異種パターン数.
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


def min_pattern_types(problem: Problem, bars: int, *, time_limit: float | None = None) -> SetupResult:
    """ちょうど bars 本を使う前提で、需要を満たす最小の異種パターン数を求める."""
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

    R = bars                                          # スロット上限（P ≤ bars）
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
    return SetupResult(
        num_patterns=len(patterns),
        patterns=tuple(patterns),
        status=status_name,
        proven=proven,
        bars=bars,
    )
