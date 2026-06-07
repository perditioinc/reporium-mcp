#!/usr/bin/env bash
# End-to-end smoke for the reporium-mcp $0 local substrate.
#   1. Bring up the stub API + mcp container (build), wait for healthy.
#   2. Assert the stub /health responds.
#   3. Exec the e2e check inside the mcp container (real mcp_server + tools/*
#      against the local stub).
#   4. Always tear down with -v.
# Exit 0 = PASS. No cloud, no credentials, $0.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(dirname "$HERE")"
# Run from the compose dir with a relative -f so no absolute path is passed to
# docker (avoids Git-Bash-on-Windows path mangling; no-op elsewhere).
cd "$COMPOSE_DIR"
COMPOSE="docker compose -f docker-compose.yml"

# The smoke only needs the internal mcp<->stub-api network link, not the host
# port. Use a high, unlikely-to-collide host port so the smoke runs even when
# 8000 is taken on the host.
export STUB_API_PORT="${STUB_API_PORT:-18000}"

cleanup() {
  echo "--- teardown ---"
  $COMPOSE down -v --remove-orphans || true
}
trap cleanup EXIT

echo "--- up (build + wait) ---"
$COMPOSE up -d --build --wait

echo "--- stub /health ---"
$COMPOSE exec -T mcp python -c "import urllib.request,sys; r=urllib.request.urlopen('http://stub-api:8000/health'); print(r.read().decode()); sys.exit(0 if r.status==200 else 1)"

echo "--- e2e: MCP tools against local stub ---"
# The image WORKDIR is already /app, so a relative module path resolves there.
# Using a relative path avoids Git-Bash-on-Windows rewriting an absolute
# in-container path into a host path. No-op on Linux/macOS.
$COMPOSE exec -T mcp python local/smoke/smoke.py

echo "--- SMOKE PASS ---"
