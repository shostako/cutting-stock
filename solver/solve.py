"""公開エントリ. Problem を受けて解を返す（唯一の外部ロジック入口, I/O 非依存）.

材料軸（使用本数最小 = arc-flow MIP on HiGHS, gap=0 証明）の単一解を返す.
段取り軸（パターン種類最小化）は分離済み（→ 姉妹プロジェクト pattern-stock）.
"""

from __future__ import annotations

from solver.arcgraph import build_arcgraph
from solver.bounds import validate_input
from solver.decompose import decompose
from solver.flow_mip import solve_flow
from solver.models import Optimality, Problem, Solution
from solver.normalize import normalize

# HiGHS は LP 下界が分数のインスタンスで分枝後、status=Optimal を返しつつ mip_gap に
# machine-epsilon の残差（2e-16〜9e-14）を残すことがある。`== 0.0` の厳密比較だと真の最適解を
# 未証明と誤標記するため、許容誤差で判定する（float 等価比較アンチパターンの回避）。
_GAP_TOL = 1e-9


def solve_material(problem: Problem, *, time_limit: float | None = None) -> Solution:
    """材料最適（使用本数最小）を arc-flow + HiGHS で厳密に解く."""
    validate_input(problem)
    norm = normalize(problem)
    graph = build_arcgraph(norm)
    flow = solve_flow(graph, time_limit=time_limit)
    patterns = decompose(graph, flow, norm.stock_length, norm.kerf)

    z = flow.bars
    L = norm.stock_length
    # 廃棄量は SPEC.md:52 の定義: z·L − 総需要長（kerf・端材・過剰生産を含み, z に対し単調）.
    # 過剰生産ピースを占有として計上すると z 増で廃棄が減る非単調が起きる（M7 bug#2）ため、
    # 占有合計でなく「需要された長さ」だけを差し引く.
    demand_length = sum(it.length * it.qty for it in problem.demand)
    total_waste = z * L - demand_length
    waste_ratio = (total_waste / (z * L)) if z > 0 else 0.0

    proven = flow.status == "Optimal" and flow.mip_gap < _GAP_TOL
    optimality = Optimality(
        status=flow.status,
        mip_gap=flow.mip_gap,
        lp_lower_bound=flow.lp_lower_bound,
        proven_optimal=proven,
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


def solve(problem: Problem, *, time_limit: float | None = None) -> Solution:
    """公開エントリ. 材料最適（使用本数最小）の単一解を返す.

    段取り軸（パターン種類最小化）は本ツールから分離済み（→ 姉妹プロジェクト pattern-stock）.
    現状 solve_material の薄いエイリアスだが、外部 I/O 層（api.py）が叩く公開境界として温存する.
    """
    return solve_material(problem, time_limit=time_limit)
