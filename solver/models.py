"""ソルバ核のデータモデル（フレームワーク非依存・依存ゼロの純 dataclass）.

設計: docs/SOLVER_DESIGN.md「データモデル」節.
- frozen で不変・副作用ゼロ（CLAUDE.md 4原則のうち冪等性を構造で担保）.
- highspy / ortools / JSON への依存をここに持ち込まない. 変換は api.py の責務.
- カット代は Model A 確定（docs/SPEC.md）: 占有 = Σℓ_j + m·k, 残材 = L − 占有.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockSpec:
    """原材料（初期設定）. 単一原材料長は要素 1 本ぶんを表す."""

    length: int  # 原材料長 L
    kerf: int    # カット代 k


@dataclass(frozen=True)
class DemandItem:
    """需要 1 種類: 長さ ℓ_i を qty 本."""

    length: int
    qty: int
    label: str = ""


@dataclass(frozen=True)
class Problem:
    """ソルバへの入力. solve(Problem) -> ParetoFrontier."""

    stock: StockSpec
    demand: tuple[DemandItem, ...]


@dataclass(frozen=True)
class Segment:
    """棒グラフ可視化のための前計算済み区間.

    offset は原材料端からの累積占有長. length 合計 = stock_length が常に成立
    （Model A 整合不変量・kerf 込み, 整合検証に使う）.
    """

    kind: str               # "piece" | "kerf" | "waste"
    offset: int
    length: int
    item_length: int | None = None
    label: str = ""


@dataclass(frozen=True)
class Pattern:
    """原材料 1 本の切り方.

    - cuts: 物理カット順に並べたピース長（棒グラフ x 座標の根拠）.
    - item_counts: (長さ, 本数) を長さ昇順で正規化した不変タプル. パターン種類の同一判定に使う.
    - run_count: この切り方を適用する原材料の本数.
    """

    stock_length: int
    cuts: tuple[int, ...]
    item_counts: tuple[tuple[int, int], ...]
    run_count: int = 1

    @property
    def type_key(self) -> tuple[int, tuple[tuple[int, int], ...]]:
        """パターン「種類」の同一判定キー（段取り種類数カウント用）. 物理カット順は無視する."""
        return (self.stock_length, self.item_counts)

    def piece_total(self) -> int:
        """ピース長の総和 Σℓ_j."""
        return sum(length * count for length, count in self.item_counts)

    def num_pieces(self) -> int:
        """このパターンが取るピース本数 m."""
        return sum(count for _, count in self.item_counts)

    def used(self, kerf: int) -> int:
        """占有長 = Σℓ_j + m·k（Model A）."""
        return self.piece_total() + self.num_pieces() * kerf

    def waste(self, kerf: int) -> int:
        """残材 = L − 占有長. 不変条件として常に >= 0 でなければならない."""
        return self.stock_length - self.used(kerf)


@dataclass(frozen=True)
class Optimality:
    """最適性の根拠（全解に必ず添付）. SPEC「自己申告で最適と言わない」を型で強制.

    proven_optimal は材料軸 gap=0 かつ LB=解値 のときだけ True.
    setup_proven は段取り軸が設定モデルB で証明済みか（フォールバック上界なら False）.
    """

    status: str
    mip_gap: float
    lp_lower_bound: float | None = None
    proven_optimal: bool = False
    setup_proven: bool = False
    timed_out: bool = False


@dataclass(frozen=True)
class Solution:
    """1 つのパレート点（ある本数バジェットでの解）."""

    bars_used: int                  # z
    patterns: tuple[Pattern, ...]
    total_waste: int
    waste_ratio: float
    num_pattern_types: int          # P
    optimality: Optimality


@dataclass(frozen=True)
class ParetoFrontier:
    """材料軸 × 段取り軸の非劣解集合. solutions は z 昇順（= P 降順）."""

    solutions: tuple[Solution, ...]
    material_optimal_idx: int
    setup_optimal_idx: int
    recommended_index: int
