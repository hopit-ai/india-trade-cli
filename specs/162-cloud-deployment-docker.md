# Spec: Cloud Deployment — Docker Compose (#162)

## Problem
The platform runs only as a local sidecar. No supported path for cloud deployment for:
- Scheduled morning briefs and alerts (always-on)
- Telegram bot
- Multi-user web access via VPS

## Solution: Tier 1 — Docker Compose

### docker/docker-compose.yml — enhanced
- Health check via `/health` endpoint
- Env file support (`--env-file .env`)
- Named volume for SQLite data + exports
- Resource limits (2 CPU, 2GB RAM)
- Log rotation

### docker/docker-compose.prod.yml — production overlay
- Caddy reverse proxy for HTTPS termination
- Automatic TLS via Let's Encrypt
- Exposed on port 443 (not 8765 directly)

### docker/Dockerfile — improvements
- Multi-stage build: build React in stage 1, copy to slim runtime
- Non-root user for security
- Healthcheck instruction

### deploy script: `scripts/deploy.sh`
- Interactive deployment script for VPS
- Pulls latest, rebuilds, restarts with zero-downtime
- Works with `docker compose up -d --build`

## Files Changed/Created
- `docker/Dockerfile` — multi-stage, non-root user, healthcheck
- `docker/docker-compose.yml` — health checks, env file, resource limits
- `docker/docker-compose.prod.yml` — Caddy HTTPS overlay
- `docker/.env.example` — template env file with all config keys
- `scripts/deploy.sh` — VPS deployment script

## Acceptance Criteria
- `docker compose -f docker/docker-compose.yml up` works
- `GET /health` returns 200 from within container
- Volumes persist data across restarts
- `.env.example` documents all required env vars
