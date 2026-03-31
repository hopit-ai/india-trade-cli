# ── India Trade CLI ──────────────────────────────────────────
# Multi-agent AI-powered stock analysis for Indian markets
#
# Build:  docker build -t india-trade-cli .
# Run:    docker run -it --env-file .env india-trade-cli
# Web:    docker run -p 8765:8765 --env-file .env india-trade-cli web

FROM python:3.13-slim

# System deps + Node.js (for claude CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Working directory
WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create data directory for persistence
RUN mkdir -p /root/.trading_platform

# Default: interactive REPL
# Override with: docker run ... python -m bot.telegram_bot (for bot)
#                docker run ... python -m web.api (for web UI)
CMD ["python", "-m", "app.main"]
