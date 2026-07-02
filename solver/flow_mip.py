"""材料最適（使用本数最小）= arc-flow MIP on HiGHS.

min（vertex0 から出るフロー）s.t. 内部頂点でフロー保存 + 各 item の総フロー == d_i.
需要は「ちょうど」満たす（過剰生産を作らない）. 余剰は loss 弧（未カットの端材）へ流れるため、
== に締めても最小本数 z* は ≥ と同一（任意の ≥ 解は余剰ピースを端材に置換して == 解にできる）.
グラフは DAG（全弧が位置を増やす）なので循環なし、vertex0→W' のフロー = 使用本数.

最適性は (a) HiGHS の mip_gap==0、(b) LP 緩和を別途解いた独立下界、の二重で裏取りする.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import highspy

from solver.arcgraph import ArcGraph

_STATUS_NAMES = {
    "kOptimal": "Optimal",
    "kInfeasible": "Infeasible",
    "kTimeLimit": "TimeLimit",
    "kUnbounded": "Unbounded",
}


def _status_str(st: object) -> str:
    for attr, label in _STATUS_NAMES.items():
        if hasattr(highspy.HighsModelStatus, attr) and st == getattr(highspy.HighsModelStatus, attr):
            return label
    return str(st)


@dataclass(frozen=True)
class FlowSolution:
    bars: int                       # 使用本数 z
    item_flow: tuple[int, ...]      # graph.item_arcs と整列したフロー値
    loss_flow: tuple[int, ...]      # graph.loss_arcs と整列したフロー値
    status: str
    mip_gap: float
    lp_lower_bound: float


def _build(graph: ArcGraph, *, integer: bool, ub: float, time_limit: float | None):
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    if time_limit is not None:
        h.setOptionValue("time_limit", float(time_limit))
    vtype = highspy.HighsVarType.kInteger if integer else highspy.HighsVarType.kContinuous

    out_v: dict[int, list] = defaultdict(list)
    in_v: dict[int, list] = defaultdict(list)
    item_by_item: dict[int, list] = defaultdict(list)

    item_vars = []
    for frm, to, i in graph.item_arcs:
        v = h.addVariable(lb=0, ub=ub, type=vtype)
        item_vars.append(v)
        out_v[frm].append(v)
        in_v[to].append(v)
        item_by_item[i].append(v)

    loss_vars = []
    for frm, to in graph.loss_arcs:
        v = h.addVariable(lb=0, ub=ub, type=vtype)
        loss_vars.append(v)
        out_v[frm].append(v)
        in_v[to].append(v)

    # フロー保存（source=0, sink=capacity を除く内部頂点）
    cap = graph.capacity
    for vtx in graph.vertices:
        if vtx == 0 or vtx == cap:
            continue
        h.addConstr(h.qsum(in_v[vtx]) == h.qsum(out_v[vtx]))

    # 需要充足（ちょうど d_i: 過剰生産を作らない. 余りは loss 弧＝未カット端材へ）
    for i, d in enumerate(graph.demands):
        h.addConstr(h.qsum(item_by_item[i]) == d)

    # 目的: vertex0 から出るフロー = 使用本数
    h.minimize(h.qsum(out_v[0]))
    return h, item_vars, loss_vars


def solve_flow(graph: ArcGraph, *, time_limit: float | None = None) -> FlowSolution:
    total_demand = sum(graph.demands)
    ub = float(total_demand)

    h, item_vars, loss_vars = _build(graph, integer=True, ub=ub, time_limit=time_limit)
    status = _status_str(h.getModelStatus())
    info = h.getInfo()
    z = round(info.objective_function_value)
    item_flow = tuple(round(h.val(v)) for v in item_vars)
    loss_flow = tuple(round(h.val(v)) for v in loss_vars)

    # LP 緩和の独立下界
    hl, _, _ = _build(graph, integer=False, ub=ub, time_limit=time_limit)
    lp_lb = float(hl.getInfo().objective_function_value)

    return FlowSolution(
        bars=z,
        item_flow=item_flow,
        loss_flow=loss_flow,
        status=status,
        mip_gap=float(info.mip_gap),
        lp_lower_bound=lp_lb,
    )
