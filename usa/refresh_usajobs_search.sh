#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "${SCRIPT_DIR}/.env.usajobs" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/.env.usajobs"
  set +a
fi

prompt_secret() {
  local var_name="$1"
  local prompt_text="$2"
  local current_value="${!var_name:-}"
  if [[ -n "${current_value}" ]]; then
    return
  fi
  if [[ ! -t 0 ]]; then
    echo "Missing ${var_name}. Set it in the environment or .env.usajobs." >&2
    exit 1
  fi
  read -r -s -p "${prompt_text}: " current_value
  echo
  if [[ -z "${current_value}" ]]; then
    echo "Missing ${var_name}. Set it in the environment or .env.usajobs." >&2
    exit 1
  fi
  export "${var_name}=${current_value}"
}

prompt_value() {
  local var_name="$1"
  local prompt_text="$2"
  local current_value="${!var_name:-}"
  if [[ -n "${current_value}" ]]; then
    return
  fi
  if [[ ! -t 0 ]]; then
    echo "Missing ${var_name}. Set it in the environment or .env.usajobs." >&2
    exit 1
  fi
  read -r -p "${prompt_text}: " current_value
  if [[ -z "${current_value}" ]]; then
    echo "Missing ${var_name}. Set it in the environment or .env.usajobs." >&2
    exit 1
  fi
  export "${var_name}=${current_value}"
}

OUTPUT_PATH="${USAJOBS_SEARCH_OUTPUT_PATH:-${SCRIPT_DIR}/data/usajobs.json}"
FRONTEND_OUTPUT_PATH="${USAJOBS_FRONTEND_OUTPUT_PATH:-${SCRIPT_DIR}/data/usajobs-lite.json}"
WHO_MAY_APPLY="${USAJOBS_WHO_MAY_APPLY:-}"
DATE_POSTED="${USAJOBS_DATE_POSTED:-}"
REMOTE_INDICATOR="${USAJOBS_REMOTE_INDICATOR:-}"
MAX_PAGES_PER_QUERY="${USAJOBS_MAX_PAGES_PER_QUERY:-0}"
TIMEOUT="${USAJOBS_TIMEOUT:-90}"
RETRIES="${USAJOBS_RETRIES:-5}"
NO_AUTO_SHARD="${USAJOBS_NO_AUTO_SHARD:-0}"
MAX_AGE_DAYS="${USAJOBS_MAX_AGE_DAYS:-7}"
FORCE_REFRESH="${USAJOBS_FORCE_REFRESH:-0}"
KEYWORDS="${USAJOBS_KEYWORDS:-}"
LOCATIONS="${USAJOBS_LOCATIONS:-}"
ORGANIZATIONS="${USAJOBS_ORGANIZATIONS:-}"
JOB_CATEGORY_CODES="${USAJOBS_JOB_CATEGORY_CODES:-}"
SCHEDULE_CODES="${USAJOBS_POSITION_SCHEDULE_TYPE_CODES:-}"
HIRING_PATHS="${USAJOBS_HIRING_PATHS:-}"

gzip_path_for() {
  local target_path="$1"
  echo "${target_path}.gz"
}

inflate_json_from_gzip_if_needed() {
  local target_path="$1"
  local gzip_path
  gzip_path="$(gzip_path_for "${target_path}")"

  if [[ ! -f "${gzip_path}" ]]; then
    return
  fi

  if [[ -f "${target_path}" && "${target_path}" -nt "${gzip_path}" ]]; then
    return
  fi

  python3 - "${gzip_path}" "${target_path}" <<'PY'
import gzip
import sys
from pathlib import Path

gzip_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])
target_path.parent.mkdir(parents=True, exist_ok=True)

with gzip.open(gzip_path, "rt", encoding="utf-8") as source:
    target_path.write_text(source.read(), encoding="utf-8")
PY
  echo "Inflated cache from ${gzip_path} -> ${target_path}"
}

payload_source_path() {
  local target_path="$1"
  local gzip_path
  gzip_path="$(gzip_path_for "${target_path}")"

  if [[ -f "${target_path}" ]]; then
    echo "${target_path}"
    return
  fi

  if [[ -f "${gzip_path}" ]]; then
    echo "${gzip_path}"
    return
  fi

  echo ""
}

payload_epoch() {
  local target_path="$1"
  local source_path
  source_path="$(payload_source_path "${target_path}")"
  python3 - "${source_path}" <<'PY'
import json
import os
import sys
from datetime import datetime, UTC
import gzip

path = sys.argv[1]
if not os.path.exists(path):
    print("")
    raise SystemExit(0)

try:
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
except Exception:
    payload = {}

fetched_at = str(payload.get("fetched_at") or "").strip()
if fetched_at:
    try:
        dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00")).astimezone(UTC)
        print(int(dt.timestamp()))
        raise SystemExit(0)
    except ValueError:
        pass

print(int(os.path.getmtime(path)))
PY
}

payload_fetched_at() {
  local target_path="$1"
  local source_path
  source_path="$(payload_source_path "${target_path}")"
  python3 - "${source_path}" <<'PY'
import json
import os
import sys
from datetime import datetime, UTC
import gzip

path = sys.argv[1]
if not os.path.exists(path):
    print("")
    raise SystemExit(0)

try:
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
except Exception:
    payload = {}

fetched_at = str(payload.get("fetched_at") or "").strip()
if fetched_at:
    print(fetched_at)
else:
    dt = datetime.fromtimestamp(os.path.getmtime(path), tz=UTC)
    print(dt.replace(microsecond=0).isoformat().replace("+00:00", "Z"))
PY
}

describe_payload_age() {
  local target_path="$1"
  local label="$2"
  local epoch
  epoch="$(payload_epoch "${target_path}")"
  if [[ -z "${epoch}" ]]; then
    echo "${label}: no cached data found."
    return
  fi

  local now age_seconds age_days fetched_at
  now="$(date +%s)"
  age_seconds=$(( now - epoch ))
  age_days="$(python3 - <<PY
age_seconds = ${age_seconds}
print(f"{age_seconds / 86400:.2f}")
PY
)"
  fetched_at="$(payload_fetched_at "${target_path}")"
  echo "${label}: fetched_at=${fetched_at} age_days=${age_days}"
}

payload_is_fresh() {
  local target_path="$1"
  if [[ "${FORCE_REFRESH}" == "1" || ! -f "${target_path}" ]]; then
    return 1
  fi

  local now epoch
  now="$(date +%s)"
  epoch="$(payload_epoch "${target_path}")"
  if [[ -z "${epoch}" ]]; then
    return 1
  fi

  if (( now - epoch < MAX_AGE_DAYS * 86400 )); then
    return 0
  fi

  return 1
}

inflate_json_from_gzip_if_needed "${OUTPUT_PATH}"
inflate_json_from_gzip_if_needed "${FRONTEND_OUTPUT_PATH}"

describe_payload_age "${OUTPUT_PATH}" "Full USAJOBS cache"
describe_payload_age "${FRONTEND_OUTPUT_PATH}" "Frontend USAJOBS cache"

if payload_is_fresh "${OUTPUT_PATH}" && payload_is_fresh "${FRONTEND_OUTPUT_PATH}"; then
  echo "USAJOBS cache is newer than ${MAX_AGE_DAYS} day(s); skipping refresh."
  exit 0
fi

echo "USAJOBS cache is stale or incomplete; refreshing now."

prompt_secret "USAJOBS_API_KEY" "Enter USAJOBS API key"
: "${USAJOBS_USER_AGENT:=${USAJOBS_EMAIL:-}}"
prompt_value "USAJOBS_USER_AGENT" "Enter USAJOBS user agent email"
export USAJOBS_API_KEY USAJOBS_USER_AGENT

args=(
  "--output" "${OUTPUT_PATH}"
  "--frontend-output" "${FRONTEND_OUTPUT_PATH}"
  "--max-pages-per-query" "${MAX_PAGES_PER_QUERY}"
  "--timeout" "${TIMEOUT}"
  "--retries" "${RETRIES}"
  "--max-age-days" "${MAX_AGE_DAYS}"
)

[[ -n "${WHO_MAY_APPLY}" ]] && args+=("--who-may-apply" "${WHO_MAY_APPLY}")
[[ -n "${DATE_POSTED}" ]] && args+=("--date-posted" "${DATE_POSTED}")
[[ -n "${REMOTE_INDICATOR}" ]] && args+=("--remote-indicator" "${REMOTE_INDICATOR}")
[[ "${NO_AUTO_SHARD}" == "1" ]] && args+=("--no-auto-shard")
[[ "${FORCE_REFRESH}" == "1" ]] && args+=("--force-refresh")

IFS='|' read -r -a keyword_array <<< "${KEYWORDS}"
for keyword in "${keyword_array[@]}"; do
  [[ -n "${keyword}" ]] && args+=("--keyword" "${keyword}")
done

IFS='|' read -r -a location_array <<< "${LOCATIONS}"
for location in "${location_array[@]}"; do
  [[ -n "${location}" ]] && args+=("--location" "${location}")
done

IFS='|' read -r -a organization_array <<< "${ORGANIZATIONS}"
for organization in "${organization_array[@]}"; do
  [[ -n "${organization}" ]] && args+=("--organization" "${organization}")
done

IFS='|' read -r -a job_category_array <<< "${JOB_CATEGORY_CODES}"
for code in "${job_category_array[@]}"; do
  [[ -n "${code}" ]] && args+=("--job-category-code" "${code}")
done

IFS='|' read -r -a schedule_array <<< "${SCHEDULE_CODES}"
for code in "${schedule_array[@]}"; do
  [[ -n "${code}" ]] && args+=("--position-schedule-type-code" "${code}")
done

IFS='|' read -r -a hiring_path_array <<< "${HIRING_PATHS}"
for path in "${hiring_path_array[@]}"; do
  [[ -n "${path}" ]] && args+=("--hiring-path" "${path}")
done

cd "${SCRIPT_DIR}"
python3 "${SCRIPT_DIR}/fetch_jobs_search.py" "${args[@]}"

describe_payload_age "${OUTPUT_PATH}" "Full USAJOBS cache after refresh"
describe_payload_age "${FRONTEND_OUTPUT_PATH}" "Frontend USAJOBS cache after refresh"
