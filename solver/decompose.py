"""フロー分解: 整数フロー → 各原材料1本のカットパターン列（純関数）.

DAG 上で 0→W' の経路を z 本取り出す. canonical order により同一 item_counts の
パターンは cuts も一致するので、item_counts でグルーピングして run_count を集計する.
"""

from __future__ import annotations

from collections import defaultdict

from solver.arcgraph import ArcGraph
from solver.flow_mip import FlowSolution
from solver.models import Pattern


def decompose(graph: ArcGraph, flow: FlowSolution, stock_length: int, kerf: int) -> list[Pattern]:
    cap = graph.capacity
    out: dict[int, list] = defaultdict(list)   # vertex -> [(kind, key, to, item)]
    rem: dict[tuple, int] = {}

    for idx, (frm, to, i) in enumerate(graph.item_arcs):
        f = flow.item_flow[idx]
        if f > 0:
            key = ("item", idx)
            out[frm].append(("item", key, to, i))
            rem[key] = f
    for idx, (frm, to) in enumerate(graph.loss_arcs):
        f = flow.loss_flow[idx]
        if f > 0:
            key = ("loss", idx)
            out[frm].append(("loss", key, to, None))
            rem[key] = f

    max_steps = len(graph.vertices) + 2
    groups: dict[tuple, list] = {}   # item_counts -> [cuts, run_count]

    for _ in range(flow.bars):
        v = 0
        cuts: list[int] = []
        counts: dict[int, int] = defaultdict(int)
        steps = 0
        while v != cap:
            steps += 1
            if steps > max_steps:
                raise RuntimeError("decompose: path did not reach sink (flow inconsistency)")
            chosen = None
            for arc in out[v]:
                if rem[arc[1]] > 0:
                    chosen = arc
                    break
            if chosen is None:
                raise RuntimeError(f"decompose: no remaining outflow at vertex {v}")
            kind, key, to, i = chosen
            rem[key] -= 1
            if kind == "item":
                length = graph.lengths[i]
                cuts.append(length)
                counts[length] += 1
            v = to

        item_counts = tuple(sorted(counts.items()))
        if item_counts in groups:
            groups[item_counts][1] += 1
        else:
            groups[item_counts] = [tuple(cuts), 1]

    patterns = [
        Pattern(stock_length=stock_length, cuts=cuts, item_counts=item_counts, run_count=run)
        for item_counts, (cuts, run) in groups.items()
    ]
    patterns.sort(key=lambda p: (-p.run_count, p.item_counts))
    return patterns
