# ==============================================================================
# FarCast DB v2 — Production Multi-Stage Dockerfile for Railway Cloud Hosting
# ==============================================================================

# ── Stage 1: Build React Frontend ─────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Production Python FastAPI Service ─────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5052

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend code & database isolation module
COPY backend/ ./backend/
COPY data/ ./data/

# Copy built React SPA static assets into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose server port
EXPOSE 5052

WORKDIR /app/backend

# Healthcheck endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-5052}/api/hardcode || exit 1

# Launch production server with Uvicorn
CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-5052}
