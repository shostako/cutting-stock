"""唯一の JSON 境界. dict <-> dataclass 変換とオーケストレーションのみ（ソルバロジック非依存）.

cli.py / http.py / 将来の desktop/batch はすべてこの層を呼ぶ＝振る舞い一致を保証する.
入出力スキーマは docs/SOLVER_DESIGN.md「ローカルAPI」節に準拠.
"""

from __future__ import annotations

from typing import Any

from solver.bounds import continuous_lower_bound
from solver.errors import InvalidInput, SolverError
from solver.models import DemandItem, Pattern, Problem, Solution, StockSpec
from solver.solve import solve

_META = {"material_solver": "arcflow+HiGHS", "pattern_solver": "CP-SAT(pool-MIP)"}


def parse_problem(payload: dict[str, Any]) -> tuple[Problem, dict[str, Any]]:
    """入力 dict から Problem と options を組み立てる. 形式不正は InvalidInput."""
    if not isinstance(payload, dict):
        raise InvalidInput("payload must be an object")
    try:
        stock = payload["stock"]
        demand = payload["demand"]
        problem = Problem(
            stock=StockSpec(length=int(stock["length"]), kerf=int(stock["kerf"])),
            demand=tuple(
                DemandItem(length=int(d["length"]), qty=int(d["qty"]), label=str(d.get("label", "")))
                for d in demand
            ),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise InvalidInput(f"malformed input: {e}") from e
    if not problem.demand:
        raise InvalidInput("demand is empty")
    return problem, payload.get("options", {}) or {}


def pattern_segments(pattern: Pattern, kerf: int, labels: dict[int, str]) -> list[dict[str, Any]]:
    """パターンを棒グラフ用の区間列に前計算する（length 合計 = stock_length, Model A 整合）.

    Model A: 各ピースの直後にカット代 k を1本消費（m ピース → m カット）. 末尾に残材.
    """
    segments: list[dict[str, Any]] = []
    offset = 0
    for length in pattern.cuts:
        segments.append({
            "kind": "piece", "offset": offset, "length": length,
            "item_length": length, "label": labels.get(length, ""),
        })
        offset += length
        if kerf > 0:
            segments.append({
                "kind": "kerf", "offset": offset, "length": kerf,
                "item_length": None, "label": "",
            })
            offset += kerf
    waste = pattern.stock_length - offset
    if waste > 0:
        segments.append({
            "kind": "waste", "offset": offset, "length": waste,
            "item_length": None, "label": "",
        })
    return segments


def _serialize_pattern(pattern: Pattern, kerf: int, labels: dict[int, str]) -> dict[str, Any]:
    return {
        "cuts": list(pattern.cuts),
        "item_counts": {str(length): cnt for length, cnt in pattern.item_counts},
        "stock_length": pattern.stock_length,
        "waste": pattern.waste(kerf),
        "run_count": pattern.run_count,
        "segments": pattern_segments(pattern, kerf, labels),
    }


def _serialize_solution(sol: Solution, kerf: int, labels: dict[int, str]) -> dict[str, Any]:
    o = sol.optimality
    return {
        "bars_used": sol.bars_used,
        "total_waste": sol.total_waste,
        "waste_ratio": round(sol.waste_ratio, 6),
        "num_pattern_types": sol.num_pattern_types,
        "optimality": {
            "status": o.status,
            "mip_gap": o.mip_gap,
            "lp_lower_bound": o.lp_lower_bound,
            "proven_optimal": o.proven_optimal,
            "patterns_min_proven": o.patterns_min_proven,
            "timed_out": o.timed_out,
        },
        "patterns": [_serialize_pattern(p, kerf, labels) for p in sol.patterns],
    }


def _serialize_result(problem: Problem, sol: Solution) -> dict[str, Any]:
    kerf = problem.stock.kerf
    labels = {it.length: it.label for it in problem.demand}
    return {
        "status": "OK",
        "validation": [],
        "input_echo": {
            "length": problem.stock.length,
            "kerf": kerf,
            "total_demand_length": sum(it.length * it.qty for it in problem.demand),
        },
        "lower_bound_bins": continuous_lower_bound(problem),
        "solution": _serialize_solution(sol, kerf, labels),
        "meta": dict(_META),
    }


def _error(code: str, message: str) -> dict[str, Any]:
    return {"status": "ERROR", "error": {"code": code, "message": message}}


def solve_from_dict(payload: dict[str, Any]) -> dict[str, Any]:
    """入力 dict を受けて解いた結果 dict を返す（CLI/HTTP 共通の唯一の入口）."""
    try:
        problem, options = parse_problem(payload)
    except SolverError as e:
        return _error(e.code, e.message)

    time_limit = options.get("time_limit_sec")
    if time_limit is not None:
        time_limit = float(time_limit)

    try:
        sol = solve(problem, time_limit=time_limit)
    except SolverError as e:
        return _error(e.code, e.message)

    return _serialize_result(problem, sol)


def validate_from_dict(payload: dict[str, Any]) -> dict[str, Any]:
    """実行可能性のみ即返し（重い最適化はしない）."""
    from solver.bounds import validate_input

    try:
        problem, _ = parse_problem(payload)
        validate_input(problem)
    except SolverError as e:
        return {"status": "OK", "feasible": False, "code": e.code, "message": e.message}
    return {
        "status": "OK",
        "feasible": True,
        "lower_bound_bins": continuous_lower_bound(problem),
    }
