#!/usr/bin/env bash
# Launch the forecast pipeline for all four companies in parallel — one process
# each. Every company's output is captured to logs/run-<TICKER>-<id>.log so the
# parallel streams don't tangle, then a summary is printed and the aggregate
# exit code reflects whether every launched run succeeded.
#
#   scripts/run/all.sh                 # run all four
#   scripts/run/all.sh --json          # pass flags straight through to run.py
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

DIR="scripts/run"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p logs
COMPANIES=(HD ADI HAS DE)

echo "▶ Launching forecast runs for ${#COMPANIES[@]} companies in parallel (id ${RUN_ID})"

pids=()
logs=()
for t in "${COMPANIES[@]}"; do
  log="logs/run-${t}-${RUN_ID}.log"
  logs+=("$log")
  bash "$DIR/company.sh" "$t" "$@" >"$log" 2>&1 &
  pids+=("$!")
done

rc=0
for i in "${!pids[@]}"; do
  if wait "${pids[$i]}"; then
    status="ok"
  else
    status="FAIL"; rc=1
  fi
  printf '  [%-4s] %-4s → %s\n' "$status" "${COMPANIES[$i]}" "${logs[$i]}"
done

echo
if [ "$rc" -eq 0 ]; then
  echo "✓ all ${#COMPANIES[@]} runs completed"
else
  echo "✗ one or more runs reported failures — see the logs above"
fi
exit "$rc"
