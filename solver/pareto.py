"""パレート前線オーケストレータ（材料軸 × 段取り軸）.

材料最適 z*（arc-flow）を一方の端点に、本数バジェット z を z*..z*+B で ε制約掃引し、
各 z で設定モデルB の最小パターン種類数 P*(z) を解く。非劣点（z 増で P が真に減る点）だけ残す.
"""

from __future__ import annotations

from solver.bounds import validate_input
from solver.models import Optimality, ParetoFrontier, Problem, Solution
from solver.setup_mip import min_pattern_types
from solver.solve import solve_material


def _build_solution(problem: Problem, z: int, z_star: int, base: Solution, setup) -> Solution:
    L = problem.stock.length
    # 廃棄量 = z·L − 総需要長（SPEC.md:52, z に単調）. 過剰生産ピースは占有でなく廃棄に計上する（M7 bug#2）.
    demand_length = sum(it.length * it.qty for it in problem.demand)
    total_waste = z * L - demand_length
    waste_ratio = (total_waste / (z * L)) if z > 0 else 0.0
    optimality = Optimality(
        status=setup.status,
        mip_gap=0.0,
        lp_lower_bound=float(z_star),                                   # 使用本数の下界 = 材料最適
        proven_optimal=(z == z_star and base.optimality.proven_optimal),  # 本数が証明済み最小なのは z* 点のみ
        setup_proven=setup.proven,                                      # P が証明済み最小か
        timed_out=setup.status != "OPTIMAL",
    )
    return Solution(
        bars_used=z,
        patterns=setup.patterns,
        total_waste=total_waste,
        waste_ratio=waste_ratio,
        num_pattern_types=setup.num_patterns,
        optimality=optimality,
    )


def solve_pareto(problem: Problem, *, max_extra_bars: int = 3, time_limit: float | None = None) -> ParetoFrontier:
    """材料最適 z* から z*+max_extra_bars までを掃引し、非劣点のパレート前線を返す."""
    validate_input(problem)
    base = solve_material(problem, time_limit=time_limit)
    z_star = base.bars_used

    raw: list[Solution] = []
    for z in range(z_star, z_star + max_extra_bars + 1):
        setup = min_pattern_types(problem, bars=z, seed_patterns=base.patterns, time_limit=time_limit)
        if setup.status not in ("OPTIMAL", "FEASIBLE"):
            continue
        raw.append(_build_solution(problem, z, z_star, base, setup))

    # 非劣点の階段: z 昇順で P が真に減る点だけ残す（z 最小は常に採用）
    frontier: list[Solution] = []
    best_P: int | None = None
    for sol in raw:
        if best_P is None or sol.num_pattern_types < best_P:
            frontier.append(sol)
            best_P = sol.num_pattern_types

    return ParetoFrontier(
        solutions=tuple(frontier),
        material_optimal_idx=0,                       # z 最小（= 廃棄最小）
        setup_optimal_idx=len(frontier) - 1,          # P 最小（= 段取り最少）
        recommended_index=0,                          # 既定は材料最優先
    )
