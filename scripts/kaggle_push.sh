#!/usr/bin/env bash
# Push a Kaggle job folder, stamping the current git commit into the script (placeholder __LEAKLENS_COMMIT__).
# Refuses to run with uncommitted changes so every Kaggle run maps to a commit.
# Usage: scripts/kaggle_push.sh kaggle/<job_folder>
set -euo pipefail
job="${1:?usage: $0 kaggle/<job_folder>}"
if [[ -n "$(git status --porcelain)" ]]; then echo "Uncommitted changes; commit first." >&2; exit 1; fi
commit="$(git rev-parse HEAD)"
tmp="$(mktemp -d)"
cp -R "$job"/. "$tmp"/
grep -rl "__LEAKLENS_COMMIT__" "$tmp" | xargs -r sed -i '' "s/__LEAKLENS_COMMIT__/$commit/g" 2>/dev/null || true
uv run kaggle kernels push -p "$tmp"
echo "pushed $job at commit $commit"
