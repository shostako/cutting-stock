"""M2 回帰: proven_optimal の float 許容誤差判定.

LP 下界が分数のインスタンスでは HiGHS が分枝し、status=Optimal でも mip_gap に
machine-epsilon 残差（2e-16〜9e-14）が残る。strict `== 0.0` だと真の最適解を未証明と
誤標記していた（M2 ウルトラコード検証が dense 体制で捕捉）。許容誤差判定で proven=True に戻ることを固定する.

これらのインスタンスは bars_used 自体は常に正しく（独立 oracle と一致）、縮約バグではない.
"""

from __future__ import annotations

import pytest

from solver.models import DemandItem, Problem, StockSpec
from solver.solve import solve_material
from solver.verify import crosscheck


def mk(length: int, kerf: int, demand: list[tuple[int, int]]) -> Problem:
    return Problem(
        stock=StockSpec(length=length, kerf=kerf),
        demand=tuple(DemandItem(length=l, qty=q, label=f"i{l}") for l, q in demand),
    )


# (problem, 期待本数) — いずれも修正前は mip_gap≈1e-16〜1e-13 で proven_optimal が偽陰性だった
FALSE_NEGATIVE_CASES = [
    (mk(220, 3, [(106, 4), (99, 2), (37, 4), (65, 2), (45, 4), (57, 4), (70, 4), (53, 1)]), 8),
    (mk(268, 0, [(115, 2), (121, 4), (76, 1), (63, 4), (65, 2), (109, 1), (87, 2)]), 6),
    (mk(270, 0, [(86, 4), (95, 4), (144, 1), (127, 4), (66, 4), (121, 4), (70, 3), (93, 2)]), 10),
    (mk(100, 5, [(10, 4), (11, 3), (13, 4), (14, 5)]), 3),
    (mk(201, 3, [(65, 2), (68, 2), (54, 5), (79, 5)]), None),
]


@pytest.mark.parametrize(
    "problem,expected_bars",
    FALSE_NEGATIVE_CASES,
    ids=[f"L{p.stock.length}k{p.stock.kerf}" for p, _ in FALSE_NEGATIVE_CASES],
)
def test_fractional_lp_bound_still_proven(problem: Problem, expected_bars: int | None) -> None:
    sol = solve_material(problem, time_limit=10.0)
    assert sol.optimality.status == "Optimal"
    assert sol.optimality.proven_optimal, f"proven_optimal false-negative: mip_gap={sol.optimality.mip_gap!r}"
    if expected_bars is not None:
        assert sol.bars_used == expected_bars
    # crosscheck も match に戻る（偽陽性 mismatch が消える）
    cc = crosscheck(problem, time_limit=10.0)
    assert cc.kind == "match", f"{cc.kind}: {cc.detail}"
