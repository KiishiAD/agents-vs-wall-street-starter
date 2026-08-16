#!/usr/bin/env bash
# End-to-end run of the four-agent pipeline.
#
#   ./scripts/forecast.sh          (or:  npm run forecast)
#
# 1. Forecast all 12 metrics for the four companies (initialiser → signal
#    extractor → analyst consensus), in parallel, printing the numbers.
# 2. Fill the four submission workbooks from that output, following the output
#    guidelines (refuses on any label/unit mismatch).
# 3. Run the organisers' own workbook check.
#
# Output lands in submission/*.xlsx. Pass any run.py flags through, e.g.
#   ./scripts/forecast.sh --json
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

echo "▶ 1/3  Pipeline — forecasting all 12 metrics"
python3 run.py --workers 4 "$@"
echo
echo "▶ 2/3  Workbooks — filling the four submission templates"
python3 scripts/pipeline_workbooks.py
echo
echo "▶ 3/3  Check — organisers' workbook validation"
npm run --silent check:forecasts
echo
echo "✓ done — submission workbooks in submission/"
