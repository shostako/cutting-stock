"""M3 段取り軸 + パレート前線のテスト.

手検証のトレードオフ例（L=8, k=0, demand {5:3, 3:5}）:
- 材料最適 z*=4（総30, ceil(30/8)=4）。4本では {5,3}×3 + {3,3}×1 で P=2 が最小。
- 5本許せば {5,3}×5（5を2本過剰生産）で P=1 に落ちる。
→ 前線は (z=4, P=2) と (z=5, P=1) の2点。
"""

from __future__ import annotations

import pytest

from solver.models import DemandItem, Problem, StockSpec
from solver.setup_mip import min_pattern_types
from solver.solve import solve, solve_material
from solver.verify import check_demand_satisfied


def mk(length: int, kerf: int, demand: list[tuple[int, int]]) -> Problem:
    return Problem(
        stock=StockSpec(length=length, kerf=kerf),
        demand=tuple(DemandItem(length=l, qty=q, label=f"i{l}") for l, q in demand),
    )


TRADEOFF = mk(8, 0, [(5, 3), (3, 5)])


def test_setup_min_patterns_at_material_optimum() -> None:
    res = min_pattern_types(TRADEOFF, bars=4, time_limit=15.0)
    assert res.status == "OPTIMAL"
    assert res.proven
    assert res.num_patterns == 2


def test_setup_min_patterns_with_extra_bar() -> None:
    res = min_pattern_types(TRADEOFF, bars=5, time_limit=15.0)
    assert res.status == "OPTIMAL"
    assert res.proven
    assert res.num_patterns == 1


def test_pareto_frontier_tradeoff() -> None:
    front = solve(TRADEOFF, mode="pareto", max_extra_bars=3, time_limit=15.0)
    # 非劣2点: (z=4,P=2) と (z=5,P=1)
    pts = [(s.bars_used, s.num_pattern_types) for s in front.solutions]
    assert pts == [(4, 2), (5, 1)]
    # インデックス
    assert front.material_optimal_idx == 0
    assert front.solutions[front.material_optimal_idx].bars_used == 4
    assert front.solutions[front.setup_optimal_idx].num_pattern_types == 1
    # 全点で需要充足 + 単調性（z昇順=P降順）
    prev_P = None
    for s in front.solutions:
        assert check_demand_satisfied(TRADEOFF, s)
        assert s.bars_used == sum(p.run_count for p in s.patterns)
        assert s.num_pattern_types == len(s.patterns)
        if prev_P is not None:
            assert s.num_pattern_types < prev_P
        prev_P = s.num_pattern_types


def test_pareto_material_point_matches_solve_material() -> None:
    front = solve(TRADEOFF, mode="pareto", time_limit=15.0)
    mat = solve_material(TRADEOFF, time_limit=15.0)
    assert front.solutions[0].bars_used == mat.bars_used
    assert front.solutions[0].optimality.proven_optimal      # z* 点は本数が証明済み最小


def test_pareto_single_point_when_already_uniform() -> None:
    # 既に P=1 が材料最適で成立 → 前線は1点
    p = mk(10, 0, [(6, 3), (4, 3)])     # z*=3, {6,4}×3 で P=1
    front = solve(p, mode="pareto", max_extra_bars=3, time_limit=15.0)
    assert front.solutions[0].num_pattern_types == 1
    assert front.material_optimal_idx == front.setup_optimal_idx == 0
    assert len(front.solutions) == 1


def test_pareto_invariants_on_kerf_instance() -> None:
    p = mk(2995, 10, [(990, 4), (560, 6)])
    front = solve(p, mode="pareto", max_extra_bars=2, time_limit=20.0)
    L, k = p.stock.length, p.stock.kerf
    for s in front.solutions:
        assert check_demand_satisfied(p, s)
        for pat in s.patterns:
            assert pat.used(k) <= L
            assert pat.waste(k) >= 0
        # 物理保存: 占有 + 端材 = 原材料総量（total_waste は SPEC:52 で別途検証）
        assert s.bars_used * L == sum(
            (pat.used(k) + pat.waste(k)) * pat.run_count for pat in s.patterns
        )
        assert s.total_waste == s.bars_used * L - sum(it.length * it.qty for it in p.demand)


def test_solve_mode_material_single_point() -> None:
    front = solve(TRADEOFF, mode="material", time_limit=15.0)
    assert len(front.solutions) == 1
    assert front.solutions[0].bars_used == 4


def test_pareto_waste_monotonic_spec52() -> None:
    """M7 bug#2 回帰: 廃棄量は本数 z に単調非減少（SPEC.md:52, z·L−総需要長）.

    TRADEOFF は z=5 で 5 を 2 本過剰生産する。旧実装は過剰生産ピースを占有計上したため
    z=5 の廃棄を 0 と誤り、z=4 の 2 より小さい非単調値を出していた。新定義では z 単調.
    """
    front = solve(TRADEOFF, mode="pareto", max_extra_bars=3, time_limit=15.0)
    L = TRADEOFF.stock.length
    demand_length = sum(it.length * it.qty for it in TRADEOFF.demand)
    prev = None
    for s in front.solutions:
        assert s.total_waste == s.bars_used * L - demand_length
        if prev is not None:
            assert s.total_waste >= prev, "廃棄量は z 増で単調非減少（SPEC.md:52）"
        prev = s.total_waste
    by_z = {s.bars_used: s.total_waste for s in front.solutions}
    assert by_z[4] == 2                      # 4·8 − 30
    assert by_z[5] == 10                     # 5·8 − 30（旧実装は過剰生産計上で 0 だった）
