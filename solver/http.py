"""HTTP 薄ラッパ（FastAPI）: GUI が叩くローカル API. ロジックは solver.api に委譲.

開発:   uv run uvicorn solver.http:app --reload         （フロントは vite dev が proxy）
本番:   web/dist をビルドしておくと、このサーバが静的フロントも同一オリジンで配信する
        （単一サーバ。GUI は相対パスで /solve 等を叩くため CORS 不要）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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


# --- 静的フロント配信（本番・単一サーバ時のみ） ---
# web/dist が存在すればルートに mount する。API ルートは上で先に登録済みなので
# /solve /validate /healthz が優先され、それ以外（/ や /assets/*）を静的が拾う。
# dist が無い開発時（vite dev が別ポートで担当）は mount せず、API だけ提供する。
_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
