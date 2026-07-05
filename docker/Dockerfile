# syntax=docker/dockerfile:1

# ---- stage 1: build the React frontend ----
FROM node:20-slim AS web
WORKDIR /web
COPY app/web/frontend/package*.json ./
RUN npm ci
COPY app/web/frontend/ ./
RUN npm run build

# ---- stage 2: python runtime ----
FROM python:3.11-slim AS runtime

# node (for the MCP filesystem server via npx) + uv (for the MCP fetch server via uvx)
RUN apt-get update && apt-get install -y --no-install-recommends \
        nodejs npm ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

WORKDIR /app

# install python deps first for better layer caching
COPY pyproject.toml ./
COPY app ./app
COPY mcp_servers.json ./
RUN pip install --no-cache-dir .

# built frontend (served by FastAPI at /) — path must match FRONTEND_DIST in server.py
COPY --from=web /web/dist ./app/web/frontend/dist

# cache the sentence-transformers reranker model on a mounted volume, not the image layer
ENV HF_HOME=/app/model_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/model_cache \
    ARGUS_BIND=0.0.0.0
RUN mkdir -p /app/model_cache /app/data

EXPOSE 8000
CMD ["python", "-m", "app.web.server"]
