#!/bin/bash
# start.sh — Sasha Health MVP startup orchestrator
#
# Usage:
#   ./scripts/start.sh              # local dev server (uvicorn)
#   ./scripts/start.sh --docker     # docker compose up
#   ./scripts/start.sh --test       # run full test suite
#   ./scripts/start.sh --health     # check if running server is healthy
#   ./scripts/start.sh --seed       # seed data from Hermes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[start.sh]${NC} $*"; }
warn() { echo -e "${YELLOW}[start.sh]${NC} $*"; }
err()  { echo -e "${RED}[start.sh]${NC} $*"; }

# ── prerequisites ────────────────────────────────────────────────────────────

check_deps() {
    log "Checking prerequisites..."
    local missing=0

    for cmd in python3 docker; do
        if ! command -v "$cmd" &>/dev/null; then
            err "Missing: $cmd"
            missing=1
        fi
    done

    if [ "$missing" -eq 1 ]; then
        err "Install missing dependencies and retry."
        exit 1
    fi

    if [ ! -f .env ]; then
        warn ".env not found — copying from .env.example"
        cp .env.example .env
        warn "Edit .env with your BOT_TOKEN and XAI_API_KEY"
    fi
}

# ── virtualenv ───────────────────────────────────────────────────────────────

ensure_venv() {
    if [ ! -d .venv ]; then
        log "Creating virtual environment..."
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -e ".[dev]" -q
}

# ── local dev ────────────────────────────────────────────────────────────────

run_local() {
    check_deps
    ensure_venv
    log "Starting local dev server on http://0.0.0.0:8000"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# ── docker ───────────────────────────────────────────────────────────────────

run_docker() {
    check_deps
    log "Building and starting Docker containers..."
    docker compose up --build -d

    log "Waiting for health check..."
    for i in $(seq 1 15); do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            log "Server is healthy at http://localhost:8000"
            docker compose ps
            return 0
        fi
        sleep 2
    done
    err "Health check timed out. Check logs: docker compose logs"
    exit 1
}

# ── health check ─────────────────────────────────────────────────────────────

run_health() {
    local url="${1:-http://localhost:8000}"
    log "Checking health at $url/health ..."
    if curl -sf "$url/health" | python3 -m json.tool; then
        log "Server is healthy"
    else
        err "Health check FAILED"
        exit 1
    fi
}

# ── test ─────────────────────────────────────────────────────────────────────

run_tests() {
    ensure_venv
    log "Running full test suite..."
    pytest -v --cov=app --cov-report=term-missing "$@"
}

# ── seed ─────────────────────────────────────────────────────────────────────

run_seed() {
    ensure_venv
    log "Seeding data from Hermes..."
    python -m app.seed "$@"
}

# ── main ─────────────────────────────────────────────────────────────────────

usage() {
    echo "Usage: $0 [--docker|--test|--health|--seed]"
    echo ""
    echo "  (no flag)      Start local dev server (uvicorn --reload)"
    echo "  --docker        Build and run via docker compose"
    echo "  --test          Run full pytest suite"
    echo "  --health [URL]  Check health endpoint (default: http://localhost:8000)"
    echo "  --seed [ARGS]   Seed data from Hermes (pass through to app.seed)"
    exit 0
}

case "${1:-}" in
    --docker)
        run_docker
        ;;
    --test)
        shift
        run_tests "$@"
        ;;
    --health)
        shift
        run_health "${1:-}"
        ;;
    --seed)
        shift
        run_seed "$@"
        ;;
    --help|-h)
        usage
        ;;
    "")
        run_local
        ;;
    *)
        err "Unknown option: $1"
        usage
        ;;
esac
