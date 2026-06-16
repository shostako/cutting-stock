# syntax=docker/dockerfile:1
#
# 単一サーバ Docker イメージ（Hugging Face Spaces / Docker SDK 想定）。
# Reactフロントを node でビルド → Python ランタイムが API と静的フロントを
# 同一オリジンで配信する（CORS不要）。HF Spaces はこれを uid 1000・port 7860 で動かす。

# ---- Stage 1: React フロントをビルド ----
FROM node:20-slim AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
# 成果物: /web/dist

# ---- Stage 2: Python ランタイム（API + 静的フロント配信） ----
FROM python:3.12-slim

# HF Spaces はコンテナを uid 1000 のユーザで実行する
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    UV_PROJECT_ENVIRONMENT=/home/user/app/.venv \
    UV_COMPILE_BYTECODE=1
WORKDIR /home/user/app

# uv（ロックファイルから再現可能に依存を入れる）
RUN pip install --no-cache-dir --user uv

# まず依存だけ入れてレイヤをキャッシュ。dev群(pytest/httpx)は除外。
COPY --chown=user:user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# アプリ本体 + ビルド済みフロント（http.py が web/dist を mount する）
COPY --chown=user:user solver/ ./solver/
COPY --chown=user:user --from=frontend /web/dist ./web/dist

EXPOSE 7860
CMD ["uv", "run", "--no-sync", "uvicorn", "solver.http:app", "--host", "0.0.0.0", "--port", "7860"]
