#!/bin/bash
# Persistent FastAPI backend for Sasha Health Mini App (launchd-friendly).
# Do not use --reload here (launchd KeepAlive would fight reloader children).
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_ROOT"

mkdir -p "$APP_ROOT/logs"

UVICORN="$APP_ROOT/.venv/bin/uvicorn"
if [[ ! -x "$UVICORN" ]]; then
  echo "ERROR: uvicorn not found at $UVICORN — run: python3 -m venv .venv && .venv/bin/pip install -e ." >&2
  exit 1
fi

# Load .env into environment for non-pydantic consumers (pydantic also reads file).
if [[ -f "$APP_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$APP_ROOT/.env"
  set +a
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

export PATH="$APP_ROOT/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export PYTHONUNBUFFERED=1

exec "$UVICORN" app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --log-level "${LOG_LEVEL:-info}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
