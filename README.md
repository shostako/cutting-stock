---
title: Cutting Stock
emoji: 📏
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# cutting-stock

> 上の YAML は [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-config-reference) 用の設定。GitHub では無視してよい。

1次元カッティングストック問題（1D Cutting Stock Problem）の**材料最適**を厳密に解く再利用ツール。

原材料長とカット代（kerf）を設定し、欲しい材料長と本数を渡すと、
**使用本数（= 単一長なら廃棄量）が最小**になる切り方を、最適性証明（arc-flow MIP の gap=0）付きで返す。
リッチな Web GUI でカットパターンを比率忠実な棒グラフで可視化し、現場向けのカット指示書（印刷 / CSV）も出力する。

> **段取り最少（カットパターン種類数の最小化）軸は本ツールから分離した。**
> パターン種類の最小化は本数を外部入力に取る別目的のため、姉妹プロジェクト **`pattern-stock`**（材料軸＋段取り軸の両方を保持）へ切り出した。
> 本リポは材料最適に専念する。

## アーキテクチャ

ソルバ核（Python）と GUI（Web）は完全に分離している。核はローカル API 越しにのみ GUI とつながるので、後で CLI / デスクトップ / バッチへ載せ替えできる。

| 層 | 技術 | 役割 |
|----|------|------|
| ソルバ核 | Python 3.12 + [HiGHS](https://highs.dev/)（`highspy`） | 材料軸 = Arc-flow MIP（使用本数最小・gap=0 証明）。`oracle.py` が独立 CP-SAT で本数を裏取り（CI 保険） |
| API 境界 | FastAPI | `/solve` `/validate` `/healthz`。JSON の入出力はここだけ |
| GUI | React + Vite + TypeScript | パターン帯・カット指示書（印刷/CSV）・過剰生産表示。チャートは全て自前（依存は react のみ） |

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

> 上記 SSOT には段取り軸 / パレート前線の記述が残るが、これは分離前（`pattern-stock` フォーク元）の履歴。本リポの現スコープは材料軸のみ。

## デプロイ（Hugging Face Spaces）

`Dockerfile` が単一サーバ（FastAPI が build済みフロントを同一オリジン配信）をそのまま起動する。
Hugging Face Spaces の Docker SDK で動かす想定（README 冒頭の frontmatter が Space 設定）。

```sh
# Space を作成（初回のみ。要 HF アカウント / トークン）
pip install -U huggingface_hub
hf auth login
hf repo create cutting-stock --repo-type space --space_sdk docker

# Space を git remote に追加して push（以後はこれで再デプロイ）
git remote add space https://huggingface.co/spaces/<user>/cutting-stock
git push space main
```

push すると HF 側で Docker をビルドし、`https://<user>-cutting-stock.hf.space` で公開される（スマホ可）。
ローカルで Docker を試すなら `docker build -t cutting-stock . && docker run -p 7860:7860 cutting-stock`。

## ライセンス

[MIT](LICENSE)
