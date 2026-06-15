"""M2 committed 回帰: arc-flow（solve_material）× oracle（CP-SAT 割当）の使用本数一致.

ハンドピック + シード固定ランダムの小インスタンスで、両定式化の最適本数が一致することを固定する.
大規模な敵対掃引は ウルトラコード workflow 側（solver.verify.crosscheck を共用）が担当する.
"""

from __future__ import annotations

import random

import pytest

from solver.models import DemandItem, Problem, StockSpec
from solver.oracle import oracle_min_bars
from solver.solve import solve_material
from solver.verify import crosscheck, random_problem


def mk(length: int, kerf: int, demand: list[tuple[int, int]]) -> Problem:
    return Problem(
        stock=StockSpec(length=length, kerf=kerf),
        demand=tuple(DemandItem(length=l, qty=q, label=f"i{l}") for l, q in demand),
    )


HANDPICKED = [
    mk(10, 0, [(5, 2)]),
    mk(2995, 10, [(990, 4)]),
    mk(100, 0, [(50, 3), (30, 2)]),
    mk(100, 0, [(40, 3), (60, 2)]),
    mk(1000, 8, [(330, 5), (250, 7), (190, 9), (120, 11)]),
    mk(500, 5, [(167, 6), (83, 9), (51, 4)]),
    mk(600, 0, [(600, 3)]),                  # 各ピースが原材料ちょうど → 1本1ピース
    mk(250, 3, [(60, 10)]),                  # 単一type多数
]


@pytest.mark.parametrize("problem", HANDPICKED, ids=lambda p: f"L{p.stock.length}k{p.stock.kerf}n{len(p.demand)}")
def test_handpicked_crosscheck(problem: Problem) -> None:
    cc = crosscheck(problem)
    assert not cc.is_bug, f"{cc.kind}: {cc.detail} | {cc.problem_repr}"
    assert cc.kind == "match", f"{cc.kind}: {cc.detail} | {cc.problem_repr}"
    assert cc.arcflow_bars == cc.oracle_bars


def test_seeded_random_crosscheck() -> None:
    """シード固定の小インスタンス 40 件で arc-flow == oracle を確認（決定的回帰）."""
    rng = random.Random(20260616)
    bugs = []
    checked = 0
    for _ in range(40):
        p = random_problem(rng, max_types=5, max_qty=6, L_range=(80, 500))
        cc = crosscheck(p, time_limit=8.0)
        if cc.kind == "inconclusive":
            continue
        checked += 1
        if cc.is_bug or cc.kind != "match":
            bugs.append(f"{cc.kind}: {cc.detail} | {cc.problem_repr}")
    assert not bugs, "arc-flow×oracle mismatch:\n" + "\n".join(bugs)
    assert checked >= 30, f"too few conclusive checks: {checked}"


def test_oracle_matches_known_small() -> None:
    """oracle 単体の妥当性: 既知の小ケース."""
    assert oracle_min_bars(mk(10, 0, [(5, 2)])).bars == 1
    assert oracle_min_bars(mk(2995, 10, [(990, 4)])).bars == 2
    assert oracle_min_bars(mk(100, 0, [(50, 3), (30, 2)])).bars == 3
