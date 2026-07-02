#!/usr/bin/env python3
"""fixtures.ts を実ソルバ出力から再生成する（手維持によるスキーマずれ事故の防止）.

使い方（リポジトリルートで）:
    uv run python web/scripts/gen_fixtures.py

App.tsx の INITIAL と同じ入力（既定スキーム=長さラベル）を solver.api.solve_from_dict に通し、
レスポンス dict をそのまま TypeScript ファイルに埋め込む。スキーマが変われば必ずここに現れる。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from solver.api import solve_from_dict  # noqa: E402

# App.tsx の INITIAL と一致させること（長さラベルスキームを焼き込み済みの形）
INITIAL_PAYLOAD = {
    "stock": {"length": 1200, "kerf": 5},
    "demand": [
        {"length": 500, "qty": 4, "label": "500"},
        {"length": 340, "qty": 6, "label": "340"},
        {"length": 290, "qty": 5, "label": "290"},
        {"length": 210, "qty": 7, "label": "210"},
    ],
}

HEADER = """\
// 実ソルバ(solver.api)の出力をそのまま埋め込んだ開発用フィクスチャ（スキーマ完全一致）。
// バックエンド未起動でもUI単体で描画・確認できる。既定スキーム=長さラベル。
// ⚠ 手で編集するな: `uv run python web/scripts/gen_fixtures.py` で再生成すること。
import type { SolveOk } from './api/types'

export const SAMPLE: SolveOk = """


def main() -> None:
    result = solve_from_dict(INITIAL_PAYLOAD)
    if result.get("status") != "OK":
        raise SystemExit(f"ソルバがOKを返さなかった: {result}")
    out = ROOT / "web" / "src" / "fixtures.ts"
    body = json.dumps(result, indent=2, ensure_ascii=False)
    out.write_text(HEADER + body + "\n", encoding="utf-8")
    sol = result["solution"]
    print(
        f"wrote {out.relative_to(ROOT)}: bars={sol['bars_used']} "
        f"types={sol['num_pattern_types']} waste={sol['total_waste']}"
    )


if __name__ == "__main__":
    main()
