#!/bin/bash
# Seed Hermes .md files into YAML frontmatter format for Project5.
#
# Usage:
#   ./scripts/seed.sh              # seed with defaults (Hermes → data/seeds/)
#   ./scripts/seed.sh --dry-run    # preview only
#   ./scripts/seed.sh --help       # full options

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment if present
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Install package in dev mode if needed
pip install -e ".[dev]" -q 2>/dev/null || true

exec python -m app.seed "$@"
