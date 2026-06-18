"""段取り軸 = 候補プール選択MIP の回帰テスト.

2026-06-18 の教訓: M7 レビューは不変条件中心で「制約は満たすが最適でない」型を見逃した。
既知最適を持つ外部ベンチマーク（Wikipedia 製紙ロール例）との突き合わせを回帰として固定する。
重いベンチマークは `@pytest.mark.slow`（既定スイートから除外、`-m slow` で実行）.
"""

from __future__ import annotations

from collections import Counter

import pytest

from solver.models import DemandItem, Problem, StockSpec
from solver.setup_mip import _enumerate_maximal_patterns, min_pattern_types
from solver.solve import solve_material


def test_enumerate_maximal_patterns_small() -> None:
    # L=8, widths=[5,3]: maximal は {5,3}=(1,1) と {3,3}=(0,2) の2つだけ
    # （{5}=5 は rem3 で 3 を追加可＝非maximal, {3,3,3}=9>8 は不可）
    pool = _enumerate_maximal_patterns([5, 3], 8, 1000)
    assert pool is not None
    assert set(pool) == {(1, 1), (0, 2)}


def test_enumerate_maximal_patterns_cap_signals_none() -> None:
    # cap を超えたら None（列挙不能シグナル = config-B フォールバックへ）
    assert _enumerate_maximal_patterns([5, 3], 8, 0) is None


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
    # 材料軸: 既知最適73本（廃棄1640 / 0.401% / 証明付き）
    mat = solve_material(WIKIPEDIA)
    assert mat.bars_used == 73
    assert mat.optimality.proven_optimal


@pytest.mark.slow
def test_wikipedia_setup_optimum_reaches_known_minimum() -> None:
    # 段取り軸: z=73 でパターン種類最小=10 を proven で到達（Wikipedia 既知最小）.
    # config-B は12止まり/proven立たずだった。プール選択MIPで真の最適到達＋証明を回帰固定.
    res = min_pattern_types(WIKIPEDIA, bars=73, time_limit=120.0)
    assert res.status == "OPTIMAL"
    assert res.proven
    assert res.num_patterns == 10
    # ちょうど73本・需要充足（≥）
    assert sum(p.run_count for p in res.patterns) == 73
    produced: Counter[int] = Counter()
    for p in res.patterns:
        for length, cnt in p.item_counts:
            produced[length] += cnt * p.run_count
    for it in WIKIPEDIA.demand:
        assert produced[it.length] >= it.qty
