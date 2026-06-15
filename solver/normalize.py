"""入力の正規化: 重複長のマージ・整数化・GCD 縮約（冪等・純関数）.

Model A の実効幅 w_i = ℓ_i + k を計算し、GCD g で割って arc-flow グラフを縮める.
占有長/残材の報告には元の ℓ_i・k を使うため、ここでは縮約後の widths と g を別に保持する.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import reduce

from solver.models import Problem


@dataclass(frozen=True)
class NormalizedProblem:
    """正規化済み問題. arc-flow グラフ構築の入力."""

    capacity: int                 # W' = L // g（縮約後のビン容量）
    g: int                        # GCD スケール係数
    stock_length: int             # 元の原材料長 L
    kerf: int                     # 元のカット代 k
    lengths: tuple[int, ...]      # 元の distinct ピース長 ℓ_i（実効幅降順に整列）
    widths: tuple[int, ...]       # 縮約後の実効幅 (ℓ_i+k)//g（lengths と整列）
    demands: tuple[int, ...]      # 必要本数 d_i（lengths と整列）
    labels: tuple[str, ...]       # 表示ラベル（lengths と整列）


def normalize(problem: Problem) -> NormalizedProblem:
    """重複長をマージし、実効幅降順（canonical order）に整列して GCD 縮約する."""
    L = problem.stock.length
    k = problem.stock.kerf

    merged: dict[int, int] = {}
    label_of: dict[int, str] = {}
    for it in problem.demand:
        merged[it.length] = merged.get(it.length, 0) + it.qty
        label_of.setdefault(it.length, it.label)

    # (実効幅, 長さ, 本数, ラベル) を実効幅降順・長さ降順で整列（対称性破りの canonical order）
    items = [(length + k, length, qty, label_of[length]) for length, qty in merged.items()]
    items.sort(key=lambda t: (-t[0], -t[1]))

    eff_widths = [w for w, _, _, _ in items]
    g = reduce(math.gcd, eff_widths)
    capacity = L // g

    return NormalizedProblem(
        capacity=capacity,
        g=g,
        stock_length=L,
        kerf=k,
        lengths=tuple(length for _, length, _, _ in items),
        widths=tuple(w // g for w in eff_widths),
        demands=tuple(qty for _, _, qty, _ in items),
        labels=tuple(lab for _, _, _, lab in items),
    )
