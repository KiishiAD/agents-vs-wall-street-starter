#!/usr/bin/env bash
# Launch the forecast pipeline for ADI. Passes through any run.py flags.
exec "$(dirname "$0")/company.sh" ADI "$@"
