"""公開エントリ. Problem を受けて解を返す（唯一の外部ロジック入口, I/O 非依存）.

M1 時点: 材料軸（使用本数最小）のみ. M3 で段取り軸 + パレート前線に拡張する.
"""

from __future__ import annotations

from solver.arcgraph import build_arcgraph
from solver.bounds import validate_input
from solver.decompose import decompose
from solver.flow_mip import solve_flow
from solver.models import Optimality, ParetoFrontier, Problem, Solution
from solver.normalize import normalize


def solve_material(problem: Problem, *, time_limit: float | None = None) -> Solution:
    """材料最適（使用本数最小）を arc-flow + HiGHS で厳密に解く."""
    validate_input(problem)
    norm = normalize(problem)
    graph = build_arcgraph(norm)
    flow = solve_flow(graph, time_limit=time_limit)
    patterns = decompose(graph, flow, norm.stock_length, norm.kerf)

    z = flow.bars
    L, k = norm.stock_length, norm.kerf
    occupancy = sum(p.used(k) * p.run_count for p in patterns)
    total_waste = z * L - occupancy
    waste_ratio = (total_waste / (z * L)) if z > 0 else 0.0

    proven = flow.status == "Optimal" and flow.mip_gap == 0.0
    optimality = Optimality(
        status=flow.status,
        mip_gap=flow.mip_gap,
        lp_lower_bound=flow.lp_lower_bound,
        proven_optimal=proven,
        setup_proven=False,
        timed_out=flow.status == "TimeLimit",
    )

    return Solution(
        bars_used=z,
        patterns=tuple(patterns),
        total_waste=total_waste,
        waste_ratio=waste_ratio,
        num_pattern_types=len(patterns),
        optimality=optimality,
    )


def solve(problem: Problem, *, time_limit: float | None = None) -> ParetoFrontier:
    """公開エントリ. M1 は材料最適の単一点のみ返す（M3 で全パレート点に拡張）."""
    sol = solve_material(problem, time_limit=time_limit)
    return ParetoFrontier(
        solutions=(sol,),
        material_optimal_idx=0,
        setup_optimal_idx=0,
        recommended_index=0,
    )
