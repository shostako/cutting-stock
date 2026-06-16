# cutting-stock

1次元カッティングストック問題（1D Cutting Stock Problem）を最適／準最適で解く再利用ツール。

原材料長とカット代（kerf）を設定し、欲しい材料長と本数を渡すと、

- **材料最適**: 使用本数（= 単一長なら廃棄量）が最小になる切り方
- **段取り最少**: カットパターンの種類数が最小になる切り方

の2軸と、その間の**パレート前線**（材料を1〜数本余分に使う代わりに段取りを減らす中間解）を提示する。
リッチな Web GUI でカットパターンを比率忠実な棒グラフで可視化する。

## アーキテクチャ

ソルバ核（Python）と GUI（Web）は完全に分離している。核はローカル API 越しにのみ GUI とつながるので、後で CLI / デスクトップ / バッチへ載せ替えできる。

| 層 | 技術 | 役割 |
|----|------|------|
| ソルバ核 | Python 3.12 + [HiGHS](https://highs.dev/)（`highspy`）/ [OR-Tools CP-SAT](https://developers.google.com/optimization) | 材料軸 = Arc-flow MIP（gap=0 証明）/ 段取り軸 = CP-SAT 設定モデル / ε制約でパレート掃引 |
| API 境界 | FastAPI | `/solve` `/validate` `/healthz`。JSON の入出力はここだけ |
| GUI | React + Vite + TypeScript | パレート散布図・パターン帯・比較モード。チャートは全て自前（依存は react のみ） |

カット代は **Model A**（各取りに1カット、`Σℓ_j + m·k ≤ L`）。詳細は [`docs/SPEC.md`](docs/SPEC.md)。

## 使い方

```sh
# 依存（uv）
uv sync

# テスト
uv run pytest

# バックエンド（端末1, リポジトリ直下）
uv run uvicorn solver.http:app --host 127.0.0.1 --port 8000

# フロント（端末2）
cd web && npm install && npm run dev   # http://localhost:5173
```

CLI 単体でも解ける（JSON を stdin → stdout）:

```sh
echo '{"stock":{"length":2995,"kerf":10},"demand":[{"length":990,"qty":5}]}' | uv run python -m solver.cli
```

## ドキュメント

- [`docs/SPEC.md`](docs/SPEC.md) — 問題仕様・目的関数・カット代の数え方
- [`docs/SOLVER_DESIGN.md`](docs/SOLVER_DESIGN.md) — ソルバ核の確定設計（SSOT）
- [`docs/GUI_DESIGN.md`](docs/GUI_DESIGN.md) — GUI の確定設計（SSOT）
- [`docs/PLAN.md`](docs/PLAN.md) — ビルド方針・技術スタック

## ライセンス

[MIT](LICENSE)
