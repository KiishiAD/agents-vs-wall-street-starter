#!/usr/bin/env bash
# Launch the forecast pipeline for HAS. Passes through any run.py flags.
exec "$(dirname "$0")/company.sh" HAS "$@"
