"""Arc-flow グラフ構築（de Carvalho の normal patterns / 対称性破り, 純関数）.

頂点 = 縮約後の到達可能位置 {0..W'}. item弧 (d, d+w_i'), loss弧 (d, W').
canonical order（実効幅降順 = item index 昇順）で配置することで、各カットパターンが
0→W' 経路に 1:1 対応する（同一パターンの順序違いを排除）.

設計の最大の実装難所. 正しさは M2 の oracle 突合（CP-SAT 割当直接解）で裏取りする.
"""

from __future__ import annotations

from dataclasses import dataclass

from solver.normalize import NormalizedProblem


@dataclass(frozen=True)
class ArcGraph:
    capacity: int                                   # W'（縮約後の sink 位置）
    vertices: tuple[int, ...]                       # 到達可能位置（昇順, 0 と W' を含む）
    item_arcs: tuple[tuple[int, int, int], ...]     # (frm, to, item_index)
    loss_arcs: tuple[tuple[int, int], ...]          # (frm, W')
    widths: tuple[int, ...]                         # 縮約後の実効幅（item index 整列）
    lengths: tuple[int, ...]                        # 元のピース長 ℓ_i（item index 整列）
    demands: tuple[int, ...]                        # 必要本数 d_i（item index 整列）


def build_arcgraph(norm: NormalizedProblem) -> ArcGraph:
    """canonical order で item弧を生成する.

    item i は「items {0..i-1} のみで到達した位置」から置き始め、while ループで同一 item の
    複数本を連結する. これにより経路上で item index は非減少（実効幅は非増加）に固定され、
    各パターンが一意の経路になる.
    """
    capacity = norm.capacity
    widths = norm.widths

    item_arcs: list[tuple[int, int, int]] = []
    reachable: set[int] = {0}                       # items {0..i-1} で到達した位置
    for i, wi in enumerate(widths):
        new_positions: set[int] = set()
        for p in sorted(reachable):
            q = p
            while q + wi <= capacity:
                item_arcs.append((q, q + wi, i))
                q += wi
                new_positions.add(q)
        reachable |= new_positions

    vertices = set(reachable)
    vertices.add(0)
    vertices.add(capacity)
    loss_arcs = [(p, capacity) for p in sorted(vertices) if p < capacity]

    return ArcGraph(
        capacity=capacity,
        vertices=tuple(sorted(vertices)),
        item_arcs=tuple(item_arcs),
        loss_arcs=tuple(loss_arcs),
        widths=widths,
        lengths=norm.lengths,
        demands=norm.demands,
    )
