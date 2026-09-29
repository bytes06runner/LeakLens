#!/usr/bin/env bash
# Build the leaklens wheel and upload it (plus tests/) as the private Kaggle Dataset <user>/leaklens-code.
# Offline Kaggle jobs install it with `pip install --no-deps`. Refuses to run with uncommitted changes so every
# Kaggle output maps to an exact git commit (recorded in CODE_VERSION.json).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -n "$(git status --porcelain)" ]; then echo "Uncommitted changes; commit first." >&2; exit 1; fi
USER_NAME=$(uv run kaggle config view | awk '/username:/{print $3}')
COMMIT=$(git rev-parse HEAD)
OUT=build/kaggle_code
rm -rf "$OUT" dist && mkdir -p "$OUT"
uv build --wheel -q
cp dist/*.whl "$OUT/"
COPYFILE_DISABLE=1 tar czf "$OUT/tests.tar.gz" tests
cp configs/*.yaml "$OUT/"
(zip -qr -X "$OUT/benchmark_injected.zip" benchmark/injected -x "*/__pycache__/*" -x "*.DS_Store")
printf '{"commit": "%s", "built_utc": "%s"}\n' "$COMMIT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OUT/CODE_VERSION.json"
printf '{"title": "leaklens-code", "id": "%s/leaklens-code", "licenses": [{"name": "other"}]}\n' "$USER_NAME" > "$OUT/dataset-metadata.json"
if uv run kaggle datasets status "$USER_NAME/leaklens-code" >/dev/null 2>&1; then
  uv run kaggle datasets version -p "$OUT" -m "code $COMMIT"
else
  uv run kaggle datasets create -p "$OUT" -q   # private by default
fi
echo "published leaklens-code @ $COMMIT (version processing on Kaggle; run scripts/check_code_version.sh before pushing jobs)"
