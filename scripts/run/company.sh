#!/usr/bin/env bash
# Launch the forecast pipeline for a single company.
#
#   scripts/run/company.sh <TICKER> [extra run.py flags...]
#   scripts/run/company.sh ADI
#   scripts/run/company.sh ADI --json
#
# Thin wrapper over `run.py --company`. A company that has no jobs configured
# yet (no source-backed profile) is reported cleanly and exits 0.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

TICKER="${1:?usage: company.sh <TICKER> [run.py flags...]}"
shift || true

echo "▶ Forecast run — ${TICKER}"
exec python3 run.py --company "$TICKER" "$@"
