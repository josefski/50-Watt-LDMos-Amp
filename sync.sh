#!/usr/bin/env bash
set -euo pipefail

PORT=/dev/ttyACM0
MP="mpremote connect ${PORT}"

# Upload all Python files in the project root
for f in *.py; do
  [ -e "$f" ] || continue
  $MP cp "$f" :
done

# Upload CSV assets (only if present)
for f in *.csv; do
  [ -e "$f" ] || continue
  $MP cp "$f" :
done

# Optional: restart so updated main.py runs
$MP reset
echo "Synced .py + .csv to Pico on ${PORT}"
