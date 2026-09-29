#!/usr/bin/env bash
# Wait until the Kaggle dataset <user>/leaklens-code serves the current git commit (Kaggle builds versions
# asynchronously and can fail silently). Exits 1 after the timeout. Usage: scripts/check_code_version.sh [minutes]
set -euo pipefail
cd "$(dirname "$0")/.."
want=$(git rev-parse HEAD); limit=${1:-15}
tmp=$(mktemp -d)
for i in $(seq 1 $((limit * 2))); do
  rm -rf "$tmp"/*
  uv run kaggle datasets download srijeetbanerjee/leaklens-code -f CODE_VERSION.json -p "$tmp" >/dev/null 2>&1 || true
  (cd "$tmp" && ls *.zip >/dev/null 2>&1 && unzip -o -q *.zip) || true
  got=$(python3 -c "import json;print(json.load(open('$tmp/CODE_VERSION.json'))['commit'])" 2>/dev/null || echo none)
  if [ "$got" = "$want" ]; then echo "dataset serves $want"; exit 0; fi
  sleep 30
done
echo "dataset still serves $got, expected $want" >&2; exit 1
