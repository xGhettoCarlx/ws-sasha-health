#!/usr/bin/env bash
# ─── Sasha Health — local deploy helper ───
# Prefer GitHub Actions (.github/workflows/deploy-sasha-health.yml) for DO.
# This script is for manual emergency deploys from a trusted machine.
#
# SEC-BWS: no default host/user/path. Export secrets in the environment:
#   DO_HOST, DO_SSH_USER, DO_SPA_REMOTE_PATH
#   DO_SSH_PORT (optional, default 22)
#   DO_SSH_KEY_FILE (optional path to private key; else ssh-agent / default key)
#
# Usage:
#   export DO_HOST=... DO_SSH_USER=... DO_SPA_REMOTE_PATH=...
#   bash deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"

: "${DO_HOST:?Set DO_HOST (deploy target host)}"
: "${DO_SSH_USER:?Set DO_SSH_USER}"
: "${DO_SPA_REMOTE_PATH:?Set DO_SPA_REMOTE_PATH (remote SPA directory)}"
DO_SSH_PORT="${DO_SSH_PORT:-22}"

SSH_OPTS=(-p "${DO_SSH_PORT}" -o IdentitiesOnly=yes)
if [[ -n "${DO_SSH_KEY_FILE:-}" ]]; then
  SSH_OPTS+=(-i "${DO_SSH_KEY_FILE}")
fi
RSYNC_RSH="ssh ${SSH_OPTS[*]}"

echo "Building frontend..."
cd "${FRONTEND_DIR}"
npm ci
npm run build

BUILD_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
COMMIT="$(git -C "${SCRIPT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
VERSION="$(node -p "require('./package.json').version")"

cat > "${FRONTEND_DIR}/dist/version.json" <<EOF
{
  "version": "${VERSION}",
  "buildTime": "${BUILD_TIME}",
  "commit": "${COMMIT}",
  "source": "local-deploy.sh"
}
EOF

echo "Rsync SPA → \${DO_SSH_USER}@\${DO_HOST}:\${DO_SPA_REMOTE_PATH}"
rsync -az --delete \
  -e "${RSYNC_RSH}" \
  "${FRONTEND_DIR}/dist/" \
  "${DO_SSH_USER}@${DO_HOST}:${DO_SPA_REMOTE_PATH}"

echo "Deploy complete — version ${VERSION} (${COMMIT})"
