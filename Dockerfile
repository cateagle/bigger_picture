# ---- Stage 1: build the frontend ----
FROM node:22-alpine AS frontend-build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

ENV VITE_API_BASE_URL=""

RUN npm run build

# ---- Stage 2: backend runtime, with the built frontend copied in ----
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/pyproject.toml backend/uv.lock* ./

RUN uv sync --frozen

COPY backend/ .

COPY --from=frontend-build /app/dist /frontend/dist
ENV FRONTEND_DIST_DIR=/frontend/dist

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
