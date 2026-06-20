"""公開エントリ. Problem を受けて解を返す（唯一の外部ロジック入口, I/O 非依存）.

辞書式最適化で単一解を返す:
  ① 使用本数を最小化（arc-flow MIP on HiGHS, gap=0 証明）.
  ② その最少本数のまま切り方（パターン種類）の数を最小化（CP-SAT 候補プール選択MIP, 証明付き）.
本数も廃棄も犠牲にせず、最少本数の中で最も切り方の少ない計画を1つ返す.
"""

from __future__ import annotations

from dataclasses import replace

from solver.arcgraph import build_arcgraph
from solver.bounds import validate_input
from solver.decompose import decompose
from solver.flow_mip import solve_flow
from solver.models import Optimality, Problem, Solution
from solver.normalize import normalize
from solver.setup_mip import min_pattern_types

# HiGHS は LP 下界が分数のインスタンスで分枝後、status=Optimal を返しつつ mip_gap に
# machine-epsilon の残差（2e-16〜9e-14）を残すことがある。`== 0.0` の厳密比較だと真の最適解を
# 未証明と誤標記するため、許容誤差で判定する（float 等価比較アンチパターンの回避）。
_GAP_TOL = 1e-9

# 第2段（切り方最小化）の安全上限. 通常は数秒で解ける（Wikipedia 例題で約2.6s）が、
# 病的に大きい入力で固まらないよう既定で上限を掛け、超過時は材料分解にフォールバックする.
_SETUP_TIME_LIMIT = 30.0


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
    """公開エントリ. 辞書式最適化で単一解を返す（① 本数最小 → ② その本数で切り方最小）.

    本数も廃棄も一切犠牲にしない. 第2段が時間内に最適到達できない場合は材料分解にフォールバックし、
    patterns_min_proven=False とする（本数の最適性 proven_optimal は常に保たれる）.
    """
    base = solve_material(problem, time_limit=time_limit)        # ① 使用本数最小 z*（証明付き）
    z = base.bars_used

    setup_limit = time_limit if time_limit is not None else _SETUP_TIME_LIMIT
    setup = min_pattern_types(                                   # ② z* 本固定で切り方の種類数を最小化
        problem, bars=z, seed_patterns=base.patterns, time_limit=setup_limit
    )

    if setup.patterns and sum(p.run_count for p in setup.patterns) == z:
        patterns = setup.patterns                               # 切り方最小の分解を採用
        patterns_min_proven = setup.proven
    else:                                                       # 異常時は材料分解にフォールバック（点を落とさない）
        patterns = base.patterns
        patterns_min_proven = False

    # 本数 z は不変ゆえ廃棄（= z·L − 需要長, Model A）も base と同一. 切り方だけ差し替える.
    optimality = replace(base.optimality, patterns_min_proven=patterns_min_proven)
    return Solution(
        bars_used=z,
        patterns=patterns,
        total_waste=base.total_waste,
        waste_ratio=base.waste_ratio,
        num_pattern_types=len(patterns),
        optimality=optimality,
    )
