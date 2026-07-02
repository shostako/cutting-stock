"""辞書式最適化（本数最小 → 切り方最小）の回帰ベンチマーク.

2026-06-18 の教訓: M7 レビューは不変条件中心で「制約は満たすが最適でない」型を見逃した。
既知最適を持つ外部ベンチマーク（Wikipedia 製紙ロール例）との突き合わせを回帰として固定する。
Wikipedia 既知最適: 73本 / 廃棄0.401% / 切り方の種類最小10通り.
重いベンチマークは `@pytest.mark.slow`（既定スイートから除外、`-m slow` で実行）.
"""

from __future__ import annotations

import pytest

from solver.models import DemandItem, Problem, StockSpec
from solver.setup_mip import _enumerate_patterns
from solver.solve import solve, solve_material


def test_enumerate_patterns_small() -> None:
    # L=8, widths=[5,3]: 有効パターン（非空）は {5}, {3}, {5,3}, {3,3} の4つ
    pool = _enumerate_patterns([5, 3], 8, 1000)
    assert pool is not None
    assert set(pool) == {(1, 0), (0, 1), (1, 1), (0, 2)}


def test_enumerate_patterns_demand_pruning() -> None:
    # 需要 d=[1,1] なら (0,2)（type2を2個）は使用不能 → 列挙から除外される
    pool = _enumerate_patterns([5, 3], 8, 1000, demands=[1, 1])
    assert pool is not None
    assert set(pool) == {(1, 0), (0, 1), (1, 1)}


def test_enumerate_patterns_cap_signals_none() -> None:
    # cap を超えたら None（列挙不能シグナル = config-B フォールバックへ）
    assert _enumerate_patterns([5, 3], 8, 0) is None


# --- Wikipedia "Cutting stock problem" 製紙ロール古典例（既知最適あり）---
WIKIPEDIA = Problem(
    stock=StockSpec(length=5600, kerf=0),
    demand=tuple(
        DemandItem(length=length, qty=qty, label=str(length))
        for length, qty in [
            (1380, 22), (1520, 25), (1560, 12), (1710, 14), (1820, 18),
            (1880, 18), (1930, 20), (2000, 10), (2050, 12), (2100, 14),
            (2140, 16), (2150, 18), (2200, 20),
        ]
    ),
)


@pytest.mark.slow
def test_wikipedia_material_optimum() -> None:
    # 第1段（材料軸）: 既知最適73本（廃棄1640 / 0.401% / 証明付き）
    mat = solve_material(WIKIPEDIA)
    assert mat.bars_used == 73
    assert mat.optimality.proven_optimal
    assert mat.total_waste == 1640


@pytest.mark.slow
def test_wikipedia_lexicographic_optimum() -> None:
    # 辞書式 solve(): 73本（本数最小・証明付き）かつ その本数で切り方10通り（最小・証明付き）.
    # 本数も廃棄も第1段と不変、切り方だけ最小化されることを回帰固定.
    sol = solve(WIKIPEDIA)
    assert sol.bars_used == 73
    assert sol.total_waste == 1640
    assert sol.optimality.proven_optimal           # 本数は最小（証明）
    assert sol.num_pattern_types == 10             # 切り方は既知最小10通り
    assert sol.optimality.patterns_min_proven      # 切り方最小も証明
    # ちょうど73本・需要充足
    assert sum(p.run_count for p in sol.patterns) == 73
    produced: dict[int, int] = {}
    for p in sol.patterns:
        for length, cnt in p.item_counts:
            produced[length] = produced.get(length, 0) + cnt * p.run_count
    for it in WIKIPEDIA.demand:
        assert produced[it.length] == it.qty           # 需要ちょうど（過剰生産なし）
