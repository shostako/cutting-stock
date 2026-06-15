"""HTTP 薄ラッパ（FastAPI）: GUI が叩くローカル API. ロジックは solver.api に委譲.

起動: uv run uvicorn solver.http:app --reload
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from solver.api import solve_from_dict, validate_from_dict

app = FastAPI(title="cutting-stock solver", version="0.1.0")


@app.post("/solve")
def solve_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    return solve_from_dict(payload)


@app.post("/validate")
def validate_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    return validate_from_dict(payload)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "solvers": ["highspy", "ortools"]}
