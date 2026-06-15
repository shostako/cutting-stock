"""CLI 薄ラッパ: stdin（または引数のファイル）から JSON を読み、結果 JSON を stdout に出す.

例:
    uv run python -m solver.cli < input.json
    uv run python -m solver.cli --validate input.json
"""

from __future__ import annotations

import argparse
import json
import sys

from solver.api import solve_from_dict, validate_from_dict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="1次元カッティングストック最適化")
    parser.add_argument("infile", nargs="?", help="入力JSON（省略時は stdin）")
    parser.add_argument("--validate", action="store_true", help="実行可能性のみ判定")
    args = parser.parse_args(argv)

    raw = open(args.infile, encoding="utf-8").read() if args.infile else sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        json.dump({"status": "ERROR", "error": {"code": "INVALID_INPUT", "message": f"invalid JSON: {e}"}},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 1

    result = validate_from_dict(payload) if args.validate else solve_from_dict(payload)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
