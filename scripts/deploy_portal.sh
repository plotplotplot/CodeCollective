#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORTAL_WEB_DIR="${PORTAL_WEB_DIR:-$ROOT_DIR/portal/web}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.portal}"
SKIP_INSTALL=0
SKIP_BUILD=0
PASSTHROUGH_ARGS=()

usage() {
  cat <<'EOF'
Usage: ./scripts/deploy_portal.sh [options] [-- <wrangler args>]

Deploys OrgPortal independently from the main codecollective.us static site.

Options:
  --env-file <path>   Optional env file to source (default: ./.env.portal if present)
  --skip-install      Skip npm install/ci
  --skip-build        Skip npm run build:cf
  -h, --help          Show this help

Environment variables:
  GOVERNANCE_API_ORIGIN   Optional; forwarded to wrangler via --var
  PIDP_API_ORIGIN         Optional; forwarded to wrangler via --var
  PORTAL_WORKER_NAME      Optional; forwarded to wrangler via --name
EOF
}

while (($#)); do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      PASSTHROUGH_ARGS+=("$@")
      break
      ;;
    *)
      PASSTHROUGH_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ ! -d "$PORTAL_WEB_DIR" ]]; then
  echo "[portal-deploy] missing portal web directory: $PORTAL_WEB_DIR" >&2
  echo "[portal-deploy] run: git submodule update --init --recursive portal" >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  echo "[portal-deploy] loading env: $ENV_FILE"
  set -a
  source "$ENV_FILE"
  set +a
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[portal-deploy] npm not found; install Node.js first" >&2
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "[portal-deploy] npx not found; install Node.js/npm first" >&2
  exit 1
fi

pushd "$PORTAL_WEB_DIR" >/dev/null

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  echo "[portal-deploy] installing dependencies"
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
fi

if [[ "$SKIP_BUILD" -eq 0 ]]; then
  echo "[portal-deploy] building portal web"
  npm run build:cf
fi

WRANGLER_ARGS=(deploy)
if [[ -n "${PORTAL_WORKER_NAME:-}" ]]; then
  WRANGLER_ARGS+=(--name "$PORTAL_WORKER_NAME")
fi
if [[ -n "${GOVERNANCE_API_ORIGIN:-}" ]]; then
  WRANGLER_ARGS+=(--var "GOVERNANCE_API_ORIGIN:${GOVERNANCE_API_ORIGIN}")
fi
if [[ -n "${PIDP_API_ORIGIN:-}" ]]; then
  WRANGLER_ARGS+=(--var "PIDP_API_ORIGIN:${PIDP_API_ORIGIN}")
fi
WRANGLER_ARGS+=("${PASSTHROUGH_ARGS[@]}")

echo "[portal-deploy] deploying with wrangler"
npx wrangler "${WRANGLER_ARGS[@]}"

popd >/dev/null

echo "[portal-deploy] done"
