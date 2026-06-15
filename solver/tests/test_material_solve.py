"""M1 材料最適コアの end-to-end テスト.

各解について不変条件（需要充足・Model A 適合・本数整合）と、
連続下界 ≤ 使用本数 ≤ FFD 上界 のサンドイッチ、proven_optimal を検証する.
"""

from __future__ import annotations

import math

import pytest

from solver.bounds import continuous_lower_bound, ffd_initial, validate_input
from solver.errors import InvalidInput, PieceTooLong
from solver.models import DemandItem, Problem, StockSpec
from solver.normalize import normalize
from solver.solve import solve_material


def mk(length: int, kerf: int, demand: list[tuple[int, int, str]]) -> Problem:
    return Problem(
        stock=StockSpec(length=length, kerf=kerf),
        demand=tuple(DemandItem(length=l, qty=q, label=lab) for l, q, lab in demand),
    )


def assert_solution_valid(sol, problem: Problem) -> None:
    L, k = problem.stock.length, problem.stock.kerf

    produced: dict[int, int] = {}
    for p in sol.patterns:
        for length, cnt in p.item_counts:
            produced[length] = produced.get(length, 0) + cnt * p.run_count
    for it in problem.demand:
        assert produced.get(it.length, 0) >= it.qty, f"demand {it.length} unmet"

    for p in sol.patterns:
        assert p.used(k) <= L, "pattern overflows stock (Model A violated)"
        assert p.waste(k) >= 0
        assert p.num_pieces() >= 1, "empty pattern should never appear at optimum"

    assert sol.bars_used == sum(p.run_count for p in sol.patterns)
    assert sol.total_waste >= 0
    assert sol.num_pattern_types == len(sol.patterns)

    lb = continuous_lower_bound(problem)
    ub, _ = ffd_initial(problem)
    assert lb <= sol.bars_used <= ub, f"bars {sol.bars_used} outside [{lb}, {ub}]"

    assert sol.optimality.proven_optimal
    assert sol.bars_used >= math.ceil(sol.optimality.lp_lower_bound - 1e-6)


def test_trivial_no_kerf() -> None:
    p = mk(10, 0, [(5, 2, "A")])
    sol = solve_material(p)
    assert sol.bars_used == 1
    assert sol.total_waste == 0
    assert_solution_valid(sol, p)


def test_kerf_reduces_capacity() -> None:
    # L=2995, k=10, 990x4 → 実効幅 1000, 2本/原材料 → 2本
    p = mk(2995, 10, [(990, 4, "A")])
    sol = solve_material(p)
    assert sol.bars_used == 2
    for pat in sol.patterns:
        assert pat.waste(10) == 995
    assert_solution_valid(sol, p)


def test_small_mixed() -> None:
    p = mk(100, 0, [(50, 3, "A"), (30, 2, "B")])
    sol = solve_material(p)
    assert sol.bars_used == 3
    assert_solution_valid(sol, p)


def test_two_exact_plus_remainder() -> None:
    # 40x3, 60x2 @ L=100: 60+40 を 2本（廃棄0）+ 残り 40 を 1本 → 3本
    p = mk(100, 0, [(40, 3, "A"), (60, 2, "B")])
    sol = solve_material(p)
    assert sol.bars_used == 3
    assert_solution_valid(sol, p)


def test_many_types_sandwich() -> None:
    p = mk(1000, 8, [(330, 5, "A"), (250, 7, "B"), (190, 9, "C"), (120, 11, "D")])
    sol = solve_material(p)
    assert_solution_valid(sol, p)


def test_piece_too_long_raises() -> None:
    p = mk(100, 5, [(100, 1, "A")])  # 100 + 5 > 100
    with pytest.raises(PieceTooLong):
        solve_material(p)


def test_invalid_input_raises() -> None:
    with pytest.raises(InvalidInput):
        validate_input(mk(0, 0, [(5, 1, "A")]))


def test_normalize_gcd_reduction() -> None:
    p = mk(1000, 0, [(200, 1, "A"), (400, 1, "B"), (600, 1, "C")])
    norm = normalize(p)
    assert norm.g == 200
    assert norm.capacity == 5
    assert norm.widths == (3, 2, 1)        # 実効幅降順に整列
    assert norm.lengths == (600, 400, 200)


def test_duplicate_lengths_merged() -> None:
    p = mk(100, 0, [(50, 2, "A"), (50, 1, "A")])
    norm = normalize(p)
    assert norm.lengths == (50,)
    assert norm.demands == (3,)
