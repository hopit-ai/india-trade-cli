#!/usr/bin/env bash
# deploy.sh — Zero-downtime deployment for india-trade-cli on a VPS
#
# Usage:
#   ./scripts/deploy.sh                 Deploy with latest code
#   ./scripts/deploy.sh --pull          Git pull before deploying
#   ./scripts/deploy.sh --prod          Use production overlay (HTTPS via Caddy)
#   ./scripts/deploy.sh --stop          Stop all containers

set -euo pipefail

COMPOSE_FILE="docker/docker-compose.yml"
PROD_FILE="docker/docker-compose.prod.yml"
PROJECT_NAME="india-trade"

WANTS_PULL=false
WANTS_PROD=false
WANTS_STOP=false

for arg in "$@"; do
  case $arg in
    --pull) WANTS_PULL=true ;;
    --prod) WANTS_PROD=true ;;
    --stop) WANTS_STOP=true ;;
  esac
done

# Determine compose command (docker compose v2 or docker-compose v1)
if docker compose version &>/dev/null 2>&1; then
  DC="docker compose"
else
  DC="docker-compose"
fi

# Build compose file list
if $WANTS_PROD; then
  COMPOSE_ARGS="-f $COMPOSE_FILE -f $PROD_FILE"
else
  COMPOSE_ARGS="-f $COMPOSE_FILE"
fi

echo "==> india-trade-cli deployment"
echo "    Compose: $COMPOSE_ARGS"

if $WANTS_STOP; then
  echo "==> Stopping containers..."
  $DC -p "$PROJECT_NAME" $COMPOSE_ARGS down
  echo "==> Stopped."
  exit 0
fi

if $WANTS_PULL; then
  echo "==> Pulling latest code..."
  git pull --ff-only
fi

# Check if .env exists in docker/ directory
if [[ ! -f "docker/.env" ]]; then
  echo ""
  echo "WARNING: docker/.env not found."
  echo "  Copy the example and fill in your values:"
  echo "  cp docker/.env.example docker/.env && nano docker/.env"
  echo ""
fi

echo "==> Building image..."
$DC -p "$PROJECT_NAME" $COMPOSE_ARGS build --pull

echo "==> Starting containers..."
$DC -p "$PROJECT_NAME" $COMPOSE_ARGS up -d --remove-orphans

echo "==> Waiting for health check..."
sleep 5

STATUS=$($DC -p "$PROJECT_NAME" $COMPOSE_ARGS ps --format json 2>/dev/null | python3 -c "
import sys, json
data = sys.stdin.read()
try:
    services = json.loads(data) if data.startswith('[') else [json.loads(l) for l in data.splitlines() if l]
    for s in services:
        state = s.get('State', s.get('Status', 'unknown'))
        print(f\"  {s.get('Service', s.get('Name', '?'))}: {state}\")
except Exception:
    print('  (could not parse status)')
" 2>/dev/null || echo "  (status unavailable)")
echo "$STATUS"

echo ""
echo "==> Deployment complete!"
echo "    App running at: http://$(hostname -I | awk '{print $1}'):8765"
if $WANTS_PROD; then
  echo "    Production: https://${DOMAIN:-yourdomain.com}"
fi
