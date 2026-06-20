"""M4 API/CLI/HTTP 境界のテスト."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from solver.api import pattern_segments, solve_from_dict, validate_from_dict
from solver.cli import main as cli_main
from solver.http import app
from solver.models import Pattern


def payload(length, kerf, demand, **options):
    return {
        "stock": {"length": length, "kerf": kerf},
        "demand": [{"length": l, "qty": q, "label": lab} for l, q, lab in demand],
        "options": options,
    }


def test_solve_from_dict_shape() -> None:
    res = solve_from_dict(payload(2995, 10, [(990, 4, "A"), (560, 6, "B")]))
    assert res["status"] == "OK"
    assert res["input_echo"]["length"] == 2995
    assert res["input_echo"]["total_demand_length"] == 990 * 4 + 560 * 6
    assert res["lower_bound_bins"] >= 1
    # 材料最適専用版: 単一解を res["solution"] で返す（旧 "pareto" 包みは廃止）
    assert "pareto" not in res
    s0 = res["solution"]
    assert {"bars_used", "total_waste", "waste_ratio", "num_pattern_types", "optimality", "patterns"} <= s0.keys()
    assert {"status", "mip_gap", "proven_optimal", "patterns_min_proven", "timed_out"} <= s0["optimality"].keys()


def test_segments_sum_equals_stock_length() -> None:
    res = solve_from_dict(payload(2995, 10, [(990, 4, "A"), (560, 6, "B")]))
    for sol in [res["solution"]]:
        for pat in sol["patterns"]:
            total = sum(seg["length"] for seg in pat["segments"])
            assert total == pat["stock_length"], f"segments sum {total} != {pat['stock_length']}"
            # offset は単調増加・連続
            off = 0
            for seg in pat["segments"]:
                assert seg["offset"] == off
                off += seg["length"]


def test_segments_model_a_kerf_after_each_piece() -> None:
    # L=2995, k=10, 990x2 → piece,kerf,piece,kerf,waste
    p = Pattern(stock_length=2995, cuts=(990, 990), item_counts=((990, 2),))
    segs = pattern_segments(p, kerf=10, labels={990: "A"})
    kinds = [s["kind"] for s in segs]
    assert kinds == ["piece", "kerf", "piece", "kerf", "waste"]
    assert segs[0]["label"] == "A"
    assert sum(s["length"] for s in segs) == 2995


def test_segments_no_kerf_segments_when_kerf_zero() -> None:
    p = Pattern(stock_length=100, cuts=(50, 50), item_counts=((50, 2),))
    segs = pattern_segments(p, kerf=0, labels={50: "X"})
    assert [s["kind"] for s in segs] == ["piece", "piece"]  # 廃棄0, kerf0
    assert sum(s["length"] for s in segs) == 100


def test_error_piece_too_long() -> None:
    res = solve_from_dict(payload(100, 5, [(100, 1, "A")]))
    assert res["status"] == "ERROR"
    assert res["error"]["code"] == "PIECE_TOO_LONG"


def test_error_invalid_input_missing_key() -> None:
    res = solve_from_dict({"demand": [{"length": 5, "qty": 1}]})  # stock 欠落
    assert res["status"] == "ERROR"
    assert res["error"]["code"] == "INVALID_INPUT"


def test_error_invalid_zero_qty() -> None:
    res = solve_from_dict(payload(100, 0, [(50, 0, "A")]))
    assert res["status"] == "ERROR"
    assert res["error"]["code"] == "INVALID_INPUT"


def test_validate_feasible_and_infeasible() -> None:
    ok = validate_from_dict(payload(1000, 5, [(300, 4, "A")]))
    assert ok["feasible"] is True and ok["lower_bound_bins"] >= 1
    ng = validate_from_dict(payload(100, 5, [(100, 1, "A")]))
    assert ng["feasible"] is False and ng["code"] == "PIECE_TOO_LONG"


def test_cli_roundtrip(tmp_path, capsys) -> None:
    f = tmp_path / "in.json"
    f.write_text(json.dumps(payload(100, 0, [(50, 3, "A"), (30, 2, "B")])), encoding="utf-8")
    code = cli_main([str(f)])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["status"] == "OK"
    assert out["solution"]["bars_used"] == 3


def test_cli_error_exit_code(tmp_path, capsys) -> None:
    f = tmp_path / "bad.json"
    f.write_text(json.dumps(payload(100, 5, [(100, 1, "A")])), encoding="utf-8")
    code = cli_main([str(f)])
    out = json.loads(capsys.readouterr().out)
    assert code == 1
    assert out["error"]["code"] == "PIECE_TOO_LONG"


def test_http_endpoints() -> None:
    client = TestClient(app)
    assert client.get("/healthz").json()["ok"] is True
    r = client.post("/solve", json=payload(100, 0, [(50, 3, "A"), (30, 2, "B")]))
    assert r.status_code == 200
    assert r.json()["status"] == "OK"
    v = client.post("/validate", json=payload(100, 5, [(100, 1, "A")]))
    assert v.json()["feasible"] is False
