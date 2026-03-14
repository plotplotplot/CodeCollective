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

prompt_secret "USAJOBS_API_KEY" "Enter USAJOBS API key"
: "${USAJOBS_USER_AGENT:=${USAJOBS_EMAIL:-}}"
prompt_value "USAJOBS_USER_AGENT" "Enter USAJOBS user agent email"
export USAJOBS_API_KEY USAJOBS_USER_AGENT

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
