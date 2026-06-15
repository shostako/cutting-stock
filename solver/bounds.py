"""入力検証と下界/上界（純関数）.

- validate_input: 退化入力を MIP に渡す前に弾く（原子性）.
- continuous_lower_bound: 使用本数の連続下界 ⌈Σ(ℓ_i+k)·d_i / L⌉（材料軸の数学下界）.
- ffd_initial: First-Fit Decreasing 貪欲で実行可能上界 + パターン（warm-start/サニティ用）.
"""

from __future__ import annotations

import math

from solver.errors import InvalidInput, PieceTooLong
from solver.models import Problem


def validate_input(problem: Problem) -> None:
    """退化入力を検出して例外を投げる. 正常なら何も返さない."""
    s = problem.stock
    if s.length <= 0:
        raise InvalidInput(f"stock length must be > 0, got {s.length}")
    if s.kerf < 0:
        raise InvalidInput(f"kerf must be >= 0, got {s.kerf}")
    if not problem.demand:
        raise InvalidInput("demand is empty")
    for it in problem.demand:
        if it.length <= 0:
            raise InvalidInput(f"demand length must be > 0, got {it.length}")
        if it.qty <= 0:
            raise InvalidInput(f"demand qty must be > 0, got {it.qty}")
        if it.length + s.kerf > s.length:
            raise PieceTooLong(
                f"piece {it.length} + kerf {s.kerf} = {it.length + s.kerf} exceeds stock {s.length}"
            )


def continuous_lower_bound(problem: Problem) -> int:
    """使用本数の連続下界. 各ビンは実効幅で高々 L しか積めない."""
    L = problem.stock.length
    k = problem.stock.kerf
    total = sum((it.length + k) * it.qty for it in problem.demand)
    return math.ceil(total / L)


def ffd_initial(problem: Problem) -> tuple[int, list[dict[int, int]]]:
    """First-Fit Decreasing 貪欲. (使用本数, 各ビンの {長さ: 本数}) を返す.

    実効幅 (ℓ+k) でビン容量 L に詰める（Model A）. 最適本数の上界になる.
    """
    L = problem.stock.length
    k = problem.stock.kerf
    pieces: list[int] = []
    for it in problem.demand:
        pieces.extend([it.length] * it.qty)
    pieces.sort(reverse=True)

    remaining: list[int] = []
    contents: list[dict[int, int]] = []
    for p in pieces:
        w = p + k
        for b in range(len(remaining)):
            if remaining[b] >= w:
                remaining[b] -= w
                contents[b][p] = contents[b].get(p, 0) + 1
                break
        else:
            remaining.append(L - w)
            contents.append({p: 1})
    return len(remaining), contents
