#!/usr/bin/env bash
# Local craft-gate runner. The consuming repo owns its test command and should
# produce coverage.xml before calling this script. Pass --fresh periodically
# to discard all cached mutation verdicts and run a complete campaign.
set -euo pipefail

BASE="origin/main"
FAST=0
FRESH=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --fast) FAST=1; shift ;;
    --fresh) FRESH=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

uv run python scripts/check_complexity_ratchet.py --path . --base "$BASE"
bash scripts/check_tidy_ratchet.sh --base "$BASE"
uv run python scripts/check_refactor_first.py --base "$BASE"

if [[ $FAST -eq 0 ]]; then
  if [[ $FRESH -eq 1 ]]; then
    rm -rf mutants
  fi
  uv run diff-cover coverage.xml --compare-branch "$BASE" --fail-under 90
  uv run mutmut run
  uv run python scripts/check_mutation_ratchet.py --base "$BASE" --threshold 80
fi

uv run python scripts/craftcov_pr_comment.py --base "$BASE" --dry-run > craftcov-report.md
uv run python scripts/craftcov.py --format sarif --no-cache --no-diff > craftcov.sarif
