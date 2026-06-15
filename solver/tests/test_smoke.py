"""M0 スモークテスト.

目的は2つ:
1. highspy / ortools(CP-SAT) の実 API がこの環境で実在し、設計が想定する呼び方で
   正しい解を返すことを裏取りする（各審査の「実機検証済み」主張を鵜呑みにしない）.
2. models.Pattern の占有長/残材が Model A（docs/SPEC.md）と整合することを固定する.
"""

from __future__ import annotations

import highspy
from ortools.sat.python import cp_model

from solver.models import Pattern


def test_highspy_integer_mip_solves_and_reports_gap() -> None:
    """min z, z >= 1.5, z 整数 → z=2, mip_gap=0, status=kOptimal.

    設計が使う API: addVariable(type=kInteger) / addConstr / minimize / getModelStatus / getInfo().mip_gap / val.
    """
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)

    z = h.addVariable(lb=0, ub=10, type=highspy.HighsVarType.kInteger)
    h.addConstr(z >= 1.5)
    h.minimize(z)

    assert h.getModelStatus() == highspy.HighsModelStatus.kOptimal
    info = h.getInfo()
    assert info.mip_gap == 0.0
    assert round(h.val(z)) == 2
    assert round(info.objective_function_value) == 2


def test_cpsat_multiplication_equality() -> None:
    """z = n·c を AddMultiplicationEquality で表し z==6 を解く（段取り軸 設定モデルB の中核 API）.

    OPTIMAL に到達し、解が n·c == z == 6 を満たすこと. BestObjectiveBound==ObjectiveValue で証明確認.
    """
    m = cp_model.CpModel()
    n = m.new_int_var(1, 6, "n")
    c = m.new_int_var(1, 6, "c")
    z = m.new_int_var(1, 36, "z")
    m.add_multiplication_equality(z, [n, c])
    m.add(z == 6)
    m.maximize(n)

    solver = cp_model.CpSolver()
    status = solver.solve(m)

    assert status == cp_model.OPTIMAL
    assert solver.value(z) == 6
    assert solver.value(n) * solver.value(c) == 6
    # best_objective_bound / objective_value は snake_case プロパティ（PascalCase は 9.15 で非推奨）.
    assert solver.best_objective_bound == solver.objective_value


def test_pattern_model_a_invariant() -> None:
    """SPEC 検算例: L=2995, ℓ=990, k=10, 990 を 2 本取り → 占有 2000, 残材 995."""
    p = Pattern(stock_length=2995, cuts=(990, 990), item_counts=((990, 2),))
    assert p.num_pieces() == 2
    assert p.piece_total() == 1980
    assert p.used(kerf=10) == 2000          # Σℓ + m·k = 1980 + 20
    assert p.waste(kerf=10) == 995          # L − 占有 = 2995 − 2000
    assert p.waste(kerf=10) >= 0            # Model A 不変条件


def test_pattern_too_long_yields_negative_waste() -> None:
    """990 を 3 本（占有 3000 > L=2995）は残材が負 = 物理的に入らない.

    実装（bounds.validate_input）はこれをハードに弾く. ここでは不変条件の検出力を固定する.
    """
    p = Pattern(stock_length=2995, cuts=(990, 990, 990), item_counts=((990, 3),))
    assert p.used(kerf=10) == 3000          # 2970 + 3·10
    assert p.waste(kerf=10) == -5           # < 0 → infeasible シグナル
