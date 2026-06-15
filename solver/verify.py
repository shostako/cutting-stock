"""M2 検証ユーティリティ: ランダムインスタンス生成 + arc-flow × oracle 突合.

committed 回帰テストと ウルトラコード workflow の両方から import して使う（DRY・突合ロジック一本化）.
"""

from __future__ import annotations

from dataclasses import dataclass

from solver.errors import SolverError
from solver.models import DemandItem, Problem, StockSpec
from solver.oracle import oracle_min_bars
from solver.solve import solve_material


def random_problem(
    rng,
    *,
    max_types: int = 6,
    max_qty: int = 8,
    length_lo: int = 1,
    L_range: tuple[int, int] = (100, 600),
    kerf_choices: tuple[int, ...] = (0, 1, 3, 5, 10),
) -> Problem:
    """シード付き RNG から1インスタンス生成. 生成時点で ℓ+k ≤ L を保証（PIECE_TOO_LONG を作らない）."""
    L = rng.randint(*L_range)
    k = rng.choice(kerf_choices)
    n = rng.randint(1, max_types)
    demand: list[DemandItem] = []
    used: set[int] = set()
    for _ in range(n):
        length = rng.randint(length_lo, L - k)
        if length in used:
            continue
        used.add(length)
        qty = rng.randint(1, max_qty)
        demand.append(DemandItem(length=length, qty=qty, label=f"i{length}"))
    return Problem(stock=StockSpec(length=L, kerf=k), demand=tuple(demand))


@dataclass(frozen=True)
class CrossCheck:
    kind: str            # match | mismatch | inconclusive | both_rejected | arcflow_only_reject
    arcflow_bars: int | None
    oracle_bars: int | None
    detail: str
    problem_repr: str

    @property
    def is_bug(self) -> bool:
        """ソルバの誤り（縮約/定式化バグ）を示すか. inconclusive はバグではない."""
        return self.kind in ("mismatch", "arcflow_only_reject")


def crosscheck(problem: Problem, *, time_limit: float = 10.0) -> CrossCheck:
    """arc-flow（solve_material）と oracle（CP-SAT 割当）の使用本数・不変条件を突合する."""
    repr_ = (
        f"L={problem.stock.length} k={problem.stock.kerf} "
        f"demand={[(d.length, d.qty) for d in problem.demand]}"
    )

    try:
        sol = solve_material(problem, time_limit=time_limit)
    except SolverError as e:
        try:
            oracle_min_bars(problem, time_limit=time_limit)
        except SolverError:
            return CrossCheck("both_rejected", None, None, f"both rejected ({type(e).__name__})", repr_)
        return CrossCheck(
            "arcflow_only_reject", None, None,
            f"arc-flow raised {type(e).__name__} but oracle accepted", repr_,
        )

    try:
        ores = oracle_min_bars(problem, time_limit=time_limit)
    except SolverError as e:
        return CrossCheck(
            "mismatch", sol.bars_used, None,
            f"oracle raised {type(e).__name__} but arc-flow solved", repr_,
        )

    L, k = problem.stock.length, problem.stock.kerf
    if not all(p.used(k) <= L and p.waste(k) >= 0 for p in sol.patterns):
        return CrossCheck("mismatch", sol.bars_used, ores.bars, "Model A invariant violated", repr_)
    if not sol.optimality.proven_optimal:
        return CrossCheck("mismatch", sol.bars_used, ores.bars, "arc-flow not proven_optimal", repr_)
    if not ores.proven_optimal:
        return CrossCheck("inconclusive", sol.bars_used, ores.bars, f"oracle not proven ({ores.status})", repr_)
    if sol.bars_used != ores.bars:
        return CrossCheck("mismatch", sol.bars_used, ores.bars, "bars mismatch", repr_)
    return CrossCheck("match", sol.bars_used, ores.bars, "match", repr_)


def check_demand_satisfied(problem: Problem, sol) -> bool:
    """解が需要を満たすか（過不足）."""
    produced: dict[int, int] = {}
    for p in sol.patterns:
        for length, cnt in p.item_counts:
            produced[length] = produced.get(length, 0) + cnt * p.run_count
    return all(produced.get(it.length, 0) >= it.qty for it in problem.demand)
