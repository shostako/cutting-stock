"""M2 committed 回帰: kerf 不変条件と退化・境界入力の挙動.

不変条件（Model A）:
- 各パターン Σℓ_j + m·k ≤ L
- 各パターン waste = L − 占有 ≥ 0
- 総量保存 z·L = Σ占有 + Σ残材（パターン集計の恒等）
"""

from __future__ import annotations

import random

import pytest

from solver.errors import InvalidInput, PieceTooLong
from solver.models import DemandItem, Problem, StockSpec
from solver.solve import solve_material
from solver.verify import check_demand_satisfied, random_problem


def mk(length: int, kerf: int, demand: list[tuple[int, int]]) -> Problem:
    return Problem(
        stock=StockSpec(length=length, kerf=kerf),
        demand=tuple(DemandItem(length=l, qty=q, label=f"i{l}") for l, q in demand),
    )


def assert_invariants(problem: Problem, sol) -> None:
    L, k = problem.stock.length, problem.stock.kerf
    occupancy = 0
    end_waste = 0
    for p in sol.patterns:
        assert p.used(k) <= L, f"overflow: {p.item_counts} used={p.used(k)} > L={L}"
        assert p.waste(k) >= 0, f"negative waste: {p.item_counts}"
        occupancy += p.used(k) * p.run_count
        end_waste += p.waste(k) * p.run_count
    # 物理保存: 占有（ピース＋kerf）＋ 端材 = 原材料総量（過剰生産に依らず常に成立）
    assert sol.bars_used * L == occupancy + end_waste
    # 廃棄量メトリクス（SPEC.md「目的関数」）: z·L − 総需要長. kerf・端材・過剰生産を含み, z に単調.
    demand_length = sum(it.length * it.qty for it in problem.demand)
    assert sol.total_waste == sol.bars_used * L - demand_length
    assert sol.total_waste >= 0
    assert check_demand_satisfied(problem, sol)


def test_invariants_seeded_random() -> None:
    rng = random.Random(424242)
    for _ in range(40):
        p = random_problem(rng, max_types=6, max_qty=8, L_range=(100, 700))
        sol = solve_material(p, time_limit=8.0)
        assert_invariants(p, sol)


def test_edge_single_type() -> None:
    sol = solve_material(mk(1000, 7, [(143, 21)]))
    assert_invariants(mk(1000, 7, [(143, 21)]), sol)


def test_edge_piece_exactly_fills_with_kerf() -> None:
    # ℓ+k = L ちょうど → 1本1ピース、端材0. ただし kerf 5×10=50 は廃棄に計上（SPEC.md「目的関数」）.
    p = mk(1000, 10, [(990, 5)])
    sol = solve_material(p)
    assert sol.bars_used == 5
    assert sol.total_waste == 50            # 端材0だが kerf 分が廃棄: z·L−総需要長 = 5000−4950
    assert_invariants(p, sol)


def test_edge_all_same_length() -> None:
    p = mk(300, 0, [(100, 9)])  # 3 per bar → 3 bars
    sol = solve_material(p)
    assert sol.bars_used == 3
    assert_invariants(p, sol)


def test_edge_coprime_widths_gcd1() -> None:
    # 互いに素な実効幅（GCD=1）→ グラフ縮約が効かない最大規模寄り
    p = mk(101, 0, [(7, 5), (11, 4), (13, 3)])
    sol = solve_material(p)
    assert_invariants(p, sol)


def test_edge_kerf_zero_vs_large() -> None:
    base = [(80, 4), (50, 6)]
    s0 = solve_material(mk(300, 0, base))
    s_big = solve_material(mk(300, 20, base))
    assert_invariants(mk(300, 0, base), s0)
    assert_invariants(mk(300, 20, base), s_big)
    # kerf が大きいほど 1 本に詰められる本数は減る → 使用本数は非減少
    assert s_big.bars_used >= s0.bars_used


def test_piece_too_long_boundary() -> None:
    # ℓ+k = L+1 → PIECE_TOO_LONG
    with pytest.raises(PieceTooLong):
        solve_material(mk(1000, 10, [(991, 1)]))


def test_zero_qty_rejected() -> None:
    with pytest.raises(InvalidInput):
        solve_material(mk(100, 0, [(50, 0)]))
