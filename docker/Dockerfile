# ── Stage 1: React build ──────────────────────────────────────
FROM node:20-slim AS web-builder

WORKDIR /build
COPY macos-app/package*.json ./
RUN npm ci --include=dev

COPY macos-app/ ./
RUN npm run build:web

# ── Stage 2: Python runtime ────────────────────────────────────
FROM python:3.12-slim

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd -m -u 1000 trader

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY pyproject.toml setup.py* requirements*.txt* ./
RUN pip install --no-cache-dir -e . 2>/dev/null || pip install --no-cache-dir uvicorn fastapi pydantic || true
RUN pip install --no-cache-dir passlib[bcrypt] uvicorn[standard] 2>/dev/null || true

# Copy application source
COPY --chown=trader:trader . .

# Copy React web build from stage 1
COPY --from=web-builder --chown=trader:trader /build/dist ./macos-app/dist

# Data directory for SQLite + exports
RUN mkdir -p /data && chown trader:trader /data
ENV TRADING_PLATFORM_DATA=/data

# Run as non-root
USER trader

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

CMD ["uvicorn", "web.api:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
