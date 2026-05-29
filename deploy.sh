#!/usr/bin/env bash
# Quick VPS deployment for CryptTraject (server + web + Caddy reverse proxy).
#
# Usage on a fresh Debian/Ubuntu VPS:
#   git clone <repo> && cd CryptTraject-Software
#   ./deploy.sh
#
# It will:
#   1. install Docker + the compose plugin if missing
#   2. create .env from .env.example on first run (then asks you to edit it)
#   3. build and start the production stack
#
# Re-run it any time to rebuild and restart after a `git pull`.
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.prod.yml"

# --- 1. Docker ---------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
    echo "==> Docker not found — installing via get.docker.com ..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER" || true
    echo "    Docker installed. You may need to log out/in for group changes."
fi

# Pick `docker compose` (v2 plugin) or fall back to `docker-compose`.
if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    echo "!! Neither 'docker compose' nor 'docker-compose' is available." >&2
    echo "   Install the Docker Compose plugin and re-run." >&2
    exit 1
fi

# --- 2. .env -----------------------------------------------------------------
if [ ! -f .env ]; then
    cp .env.example .env
    echo
    echo "==> Created .env from .env.example."
    echo "    Edit it now (set SITE_ADDRESS to your domain + ACME_EMAIL for HTTPS),"
    echo "    then re-run ./deploy.sh."
    echo "    Leaving SITE_ADDRESS=:80 serves plain HTTP on the VPS IP."
    exit 0
fi

# --- 3. Build & start --------------------------------------------------------
echo "==> Building and starting the stack ..."
$DC -f "$COMPOSE_FILE" up -d --build

echo
echo "==> Done. Current status:"
$DC -f "$COMPOSE_FILE" ps

# Show the effective address from .env for convenience.
SITE_ADDRESS="$(grep -E '^SITE_ADDRESS=' .env | head -1 | cut -d= -f2-)"
echo
case "$SITE_ADDRESS" in
    :80|"")
        echo "    Landing page : http://<your-VPS-IP>/"
        echo "    API base     : http://<your-VPS-IP>/api"
        ;;
    *)
        echo "    Landing page : https://${SITE_ADDRESS}/"
        echo "    API base     : https://${SITE_ADDRESS}/api"
        ;;
esac
echo "    Desktop client: point --server at the API base above."
