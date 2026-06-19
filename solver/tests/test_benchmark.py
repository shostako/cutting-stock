"""材料軸（使用本数最小）の回帰ベンチマーク.

2026-06-18 の教訓: M7 レビューは不変条件中心で「制約は満たすが最適でない」型を見逃した。
既知最適を持つ外部ベンチマーク（Wikipedia 製紙ロール例）との突き合わせを回帰として固定する。
重いベンチマークは `@pytest.mark.slow`（既定スイートから除外、`-m slow` で実行）.
"""

from __future__ import annotations

import pytest

from solver.models import DemandItem, Problem, StockSpec
from solver.solve import solve_material


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
    assert mat.total_waste == 1640
