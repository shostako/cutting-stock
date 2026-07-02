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
- `src/components/` — InputPanel / MetricsCard / PatternView(+PatternBar) / OptimalityBadge
- `src/colors.ts` `src/labels.ts` `src/format.ts` `src/report.ts` — 色割当・ラベル・整形・指示書生成
- チャートは全て自前（棒=幅%の比率忠実 HTML）。依存は react/react-dom のみ。

## ビルド

```sh
npm run build    # tsc 型チェック + vite build → dist/
```

## テスト

```sh
npm test         # vitest: ロジック層（report/labels/colors）のユニットテスト
```

E2E スモーク（実ソルバ + ビルド済み GUI の通し検証。要 build と Python playwright）:

```sh
npm run build
cd .. && python3 web/e2e/smoke.py
```

## フィクスチャ再生成

`src/fixtures.ts` は手で編集しない。スキーマ変更時は実ソルバ出力から再生成する:

```sh
# リポジトリ直下で
uv run python web/scripts/gen_fixtures.py
```
