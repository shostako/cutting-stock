"""CP-SAT 割当モデルによる独立 ground-truth（M2 検証専用）.

材料軸の主筋ではない（per-bin 割当は対称性と弱い LP 緩和で中規模 gap が閉じない）。
小規模インスタンスで arc-flow の使用本数を「別定式化で」裏取りするためだけに使う。
arc-flow と oracle が食い違えば、どちらか（多くは arc-flow の normal-patterns 縮約）のバグ.
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from solver.bounds import ffd_initial, validate_input
from solver.models import Problem

_STATUS_NAMES = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


@dataclass(frozen=True)
class OracleResult:
    bars: int
    status: str
    proven_optimal: bool


def oracle_min_bars(problem: Problem, *, time_limit: float | None = None) -> OracleResult:
    """使用本数最小を CP-SAT 割当モデルで解く（独立 ground-truth）.

    use[b]∈{0,1}, x[b,j]∈[0, min(d_j, L//w_j)] 整数.
    容量 Σ_j w_j·x[b,j] ≤ L·use[b] / 需要 Σ_b x[b,j] ≥ d_j / 対称性破り use[b] ≥ use[b+1] / min Σ use[b].
    ビン数上限 B は FFD 上界（feasible を保証）.
    """
    validate_input(problem)
    L = problem.stock.length
    k = problem.stock.kerf

    merged: dict[int, int] = {}
    for it in problem.demand:
        merged[it.length] = merged.get(it.length, 0) + it.qty
    lengths = list(merged.keys())
    demands = [merged[length] for length in lengths]
    widths = [length + k for length in lengths]
    n = len(lengths)

    B, _ = ffd_initial(problem)

    model = cp_model.CpModel()
    use = [model.new_bool_var(f"use_{b}") for b in range(B)]
    x = [
        [model.new_int_var(0, min(demands[j], L // widths[j]), f"x_{b}_{j}") for j in range(n)]
        for b in range(B)
    ]

    for b in range(B):
        model.add(sum(widths[j] * x[b][j] for j in range(n)) <= L * use[b])
    for j in range(n):
        model.add(sum(x[b][j] for b in range(B)) >= demands[j])
    for b in range(B - 1):
        model.add(use[b] >= use[b + 1])
    model.minimize(sum(use))

    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = float(time_limit)
    status = solver.solve(model)

    status_name = _STATUS_NAMES.get(status, str(status))
    bars = round(solver.objective_value) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else -1
    proven = status == cp_model.OPTIMAL and solver.best_objective_bound == solver.objective_value
    return OracleResult(bars=bars, status=status_name, proven_optimal=proven)
