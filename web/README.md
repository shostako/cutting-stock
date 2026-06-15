# web — cutting-stock GUI

1次元カッティングストック最適化の Web GUI（React + Vite + TypeScript）。
ソルバ核（Python）とは `http.py`（FastAPI）越しにローカル接続する。設計は `../docs/GUI_DESIGN.md`。

## 起動

2つの端末で：

```sh
# 端末1: バックエンド（リポジトリ直下で）
uv run uvicorn solver.http:app --host 127.0.0.1 --port 8000

# 端末2: フロント（このディレクトリで）
npm install      # 初回のみ
npm run dev      # http://localhost:5173
```

dev サーバは `/solve` `/validate` `/healthz` を `127.0.0.1:8000` へ proxy する（`vite.config.ts`）。
バックエンド未起動でも、初期表示は `src/fixtures.ts`（実ソルバ出力）で全 UI を描画できる。

## 構成

- `src/api/` — 型定義（`types.ts`）と fetch クライアント（`client.ts`）
- `src/components/` — InputPanel / ParetoChart / MetricsCard / PatternView(+PatternBar) / ComparePanel / OptimalityBadge
- `src/colors.ts` `src/format.ts` — 色割当・数値整形
- チャートは全て自前（棒=幅%の比率忠実 HTML、散布図=SVG）。依存は react/react-dom のみ。

## ビルド

```sh
npm run build    # tsc 型チェック + vite build → dist/
```
