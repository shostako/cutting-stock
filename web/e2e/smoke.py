#!/usr/bin/env python3
"""E2E スモークテスト: ビルド済み GUI + 実ソルバを通しで叩く.

使い方（リポジトリルートで, 事前に web を build しておく）:
    cd web && npm run build && cd ..
    uv run python web/e2e/smoke.py

サーバは自前で起動・終了する（ポート 8399）。検証項目:
- デモボタンが demo1 / demo2 の2つ
- demo1（Wikipedia 例題）: 73本 / 切り方10通り / 両方の証明バッジ / 過剰生産テーブル不出現
- demo2（ランダム）×3回: エラーなし / 過剰生産テーブル不出現（需要 == の約束の通し検証）
"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PORT = 8399
BASE = f"http://localhost:{PORT}"


def wait_healthz(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/healthz", timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise SystemExit("サーバが起動しない（healthz 不達）")


def run_checks() -> list[str]:
    from playwright.sync_api import sync_playwright

    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        print(("ok  " if cond else "FAIL") + f"  {msg}")
        if not cond:
            failures.append(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        page.goto(BASE)
        page.wait_for_load_state("networkidle")

        demos = page.locator(".demo-btn").all_text_contents()
        check(demos == ["demo1", "demo2"], f"デモボタンは demo1/demo2 の2つ（実際: {demos}）")

        def solve_and_wait(timeout_ms: int = 120_000) -> None:
            page.locator(".solve-btn").click()
            page.wait_for_function(
                "!document.querySelector('.solve-btn').disabled", timeout=timeout_ms
            )

        # demo1 = Wikipedia 既知最適（73本 / 10通り / 両証明）
        page.locator(".demo-btn", has_text="demo1").click()
        solve_and_wait()
        check(page.locator(".error-banner").count() == 0, "demo1: エラーなし")
        check(page.locator(".overproduction").count() == 0, "demo1: 過剰生産テーブル不出現")
        body = page.locator(".metrics-card, .app").first.inner_text()
        check("73" in body, "demo1: 使用本数 73 本")
        check("10" in body, "demo1: 切り方 10 通り")
        badges = page.locator(".right").first.inner_text()
        check("本数は最少" in badges and "切り方も最小" in badges, "demo1: 両方の証明バッジ表示")

        # demo2 = ランダム ×3（需要 == の約束を通しで検証）
        for i in range(3):
            page.locator(".demo-btn", has_text="demo2").click()
            solve_and_wait()
            check(page.locator(".error-banner").count() == 0, f"demo2 run{i + 1}: エラーなし")
            check(
                page.locator(".overproduction").count() == 0,
                f"demo2 run{i + 1}: 過剰生産テーブル不出現",
            )

        browser.close()
    return failures


def main() -> None:
    if not (ROOT / "web" / "dist" / "index.html").exists():
        raise SystemExit("web/dist がない。先に `cd web && npm run build` を実行しろ")
    server = subprocess.Popen(
        ["uv", "run", "uvicorn", "solver.http:app", "--port", str(PORT)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_healthz()
        failures = run_checks()
    finally:
        server.terminate()
        server.wait(timeout=10)
    if failures:
        print(f"\n{len(failures)} 件失敗")
        sys.exit(1)
    print("\n全チェック通過")


if __name__ == "__main__":
    main()
