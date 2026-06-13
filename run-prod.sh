#!/usr/bin/env bash
#
# Run the PaperAgent production stack (db + app + frontend + Caddy).
#
# Usage:
#   ./run-prod.sh up        # build images and start everything (default)
#   ./run-prod.sh down      # stop and remove containers (volumes kept)
#   ./run-prod.sh restart   # restart without rebuilding
#   ./run-prod.sh rebuild   # pull latest code-free deps, rebuild, restart
#   ./run-prod.sh logs      # follow logs for all services
#   ./run-prod.sh ps        # show container status
#
set -euo pipefail

# Always run from the directory this script lives in (the repo root).
cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.prod.yml"
COMPOSE="docker compose -f ${COMPOSE_FILE}"

# --- preflight checks -------------------------------------------------------
if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "ERROR: ${COMPOSE_FILE} not found. Run this from the repo root." >&2
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "ERROR: .env not found. Copy .env.example to .env and fill in your" >&2
  echo "       production values (OPENAI_API_KEY, JWT_SECRET, POSTGRES_*)." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: 'docker compose' is not available. Install Docker Engine +" >&2
  echo "       the Compose plugin first." >&2
  exit 1
fi

cmd="${1:-up}"

case "${cmd}" in
  up)
    echo ">> Building and starting the production stack..."
    ${COMPOSE} up -d --build
    echo ">> Done. Status:"
    ${COMPOSE} ps
    ;;
  down)
    echo ">> Stopping the production stack (volumes are kept)..."
    ${COMPOSE} down
    ;;
  restart)
    echo ">> Restarting services (no rebuild)..."
    ${COMPOSE} restart
    ;;
  rebuild)
    echo ">> Rebuilding images and recreating containers..."
    ${COMPOSE} up -d --build --force-recreate
    ${COMPOSE} ps
    ;;
  logs)
    ${COMPOSE} logs -f
    ;;
  ps)
    ${COMPOSE} ps
    ;;
  *)
    echo "Unknown command: ${cmd}" >&2
    echo "Usage: $0 {up|down|restart|rebuild|logs|ps}" >&2
    exit 1
    ;;
esac
