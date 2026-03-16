#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "${SCRIPT_DIR}/.env.usajobs" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/.env.usajobs"
  set +a
fi

MAX_PAGES="${USAJOBS_MAX_PAGES:-0}"
ALL_POSTINGS="${USAJOBS_ALL_POSTINGS:-0}"
START_POSITION_OPEN_DATE="${USAJOBS_START_POSITION_OPEN_DATE:-}"
END_POSITION_OPEN_DATE="${USAJOBS_END_POSITION_OPEN_DATE:-}"
START_POSITION_CLOSE_DATE="${USAJOBS_START_POSITION_CLOSE_DATE:-}"
END_POSITION_CLOSE_DATE="${USAJOBS_END_POSITION_CLOSE_DATE:-}"
HIRING_AGENCY_CODES="${USAJOBS_HIRING_AGENCY_CODES:-}"
HIRING_DEPARTMENT_CODES="${USAJOBS_HIRING_DEPARTMENT_CODES:-}"
POSITION_SERIES="${USAJOBS_POSITION_SERIES:-}"
ANNOUNCEMENT_NUMBERS="${USAJOBS_ANNOUNCEMENT_NUMBERS:-}"
CONTROL_NUMBERS="${USAJOBS_CONTROL_NUMBERS:-}"

args=(
  "--output" "${SCRIPT_DIR}/data/usajobs.json"
  "--max-pages" "${MAX_PAGES}"
)

if [[ "${ALL_POSTINGS}" == "1" ]]; then
  args+=("--all-postings")
fi

[[ -n "${START_POSITION_OPEN_DATE}" ]] && args+=("--start-position-open-date" "${START_POSITION_OPEN_DATE}")
[[ -n "${END_POSITION_OPEN_DATE}" ]] && args+=("--end-position-open-date" "${END_POSITION_OPEN_DATE}")
[[ -n "${START_POSITION_CLOSE_DATE}" ]] && args+=("--start-position-close-date" "${START_POSITION_CLOSE_DATE}")
[[ -n "${END_POSITION_CLOSE_DATE}" ]] && args+=("--end-position-close-date" "${END_POSITION_CLOSE_DATE}")

IFS='|' read -r -a hiring_agency_array <<< "${HIRING_AGENCY_CODES}"
for code in "${hiring_agency_array[@]}"; do
  [[ -n "${code}" ]] && args+=("--hiring-agency-code" "${code}")
done

IFS='|' read -r -a hiring_department_array <<< "${HIRING_DEPARTMENT_CODES}"
for code in "${hiring_department_array[@]}"; do
  [[ -n "${code}" ]] && args+=("--hiring-department-code" "${code}")
done

IFS='|' read -r -a position_series_array <<< "${POSITION_SERIES}"
for series in "${position_series_array[@]}"; do
  [[ -n "${series}" ]] && args+=("--position-series" "${series}")
done

IFS='|' read -r -a announcement_array <<< "${ANNOUNCEMENT_NUMBERS}"
for announcement in "${announcement_array[@]}"; do
  [[ -n "${announcement}" ]] && args+=("--announcement-number" "${announcement}")
done

IFS='|' read -r -a control_array <<< "${CONTROL_NUMBERS}"
for control in "${control_array[@]}"; do
  [[ -n "${control}" ]] && args+=("--usajobs-control-number" "${control}")
done

cd "${SCRIPT_DIR}"
python3 "${SCRIPT_DIR}/fetch_jobs.py" "${args[@]}"
