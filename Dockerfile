# syntax=docker/dockerfile:1
# One image: the FastAPI proxy on :8001 that also serves the built React frontend at "/".

# ── Stage 1: build the Vite/React frontend (reads frontend/public.env for the Supabase URL+key) ──
FROM node:22-slim AS frontend
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build                       # → /app/frontend/dist

# ── Stage 2: the backend (uv + Python 3.13), serving the proxy + the dist from stage 1 ──
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS runtime
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app/backend

# Install deps first so this layer caches independently of source changes.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY backend/ ./
# main.py serves app.frontend("../../frontend/dist"), i.e. /app/frontend/dist relative to src/
COPY --from=frontend /app/frontend/dist /app/frontend/dist

WORKDIR /app/backend/src
ENV PORT=8001
EXPOSE 8001
# SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY / SUPABASE_SERVICE_KEY must be supplied at runtime (see compose).
CMD uv run --no-sync uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}
