#!/usr/bin/env bash
# Local craft-gate runner. The consuming repo owns its test command and should
# produce coverage.xml before calling this script (the behaviour-coverage run
# produces its own). Configure mutmut's
# pytest_add_cli_args_test_selection for a focused mutation test suite; the
# normal CI test job still runs the complete suite. Pass --fresh periodically
# to discard all cached mutation verdicts and run a complete campaign.
set -euo pipefail

BASE="origin/main"
FAST=0
FRESH=0
MUTATION=auto
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --fast) FAST=1; shift ;;
    --fresh) FRESH=1; shift ;;
    --mutation) MUTATION=on; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

uv run --with-requirements scripts/gate-requirements.txt python scripts/check_complexity_ratchet.py --path . --base "$BASE"
bash scripts/check_tidy_ratchet.sh --base "$BASE"
uv run --with-requirements scripts/gate-requirements.txt python scripts/check_refactor_first.py --base "$BASE"

# Whether a test gate applies here is scripts/gate_config.py's call (pyproject.toml's
# [tool.craft-gate]); a misconfigured gate stops the run, a deliberate opt-out is reported.
GATE_ENV="$(mktemp)"
trap 'rm -f "$GATE_ENV"' EXIT
gate_runs() {
  : > "$GATE_ENV"
  GITHUB_OUTPUT="$GATE_ENV" python3 scripts/gate_config.py "$1" || exit 1
  grep -q '^status=run$' "$GATE_ENV"
}
gate_setting() { grep "^$1=" "$GATE_ENV" | cut -d= -f2-; }
# diff-cover's --exclude takes globs; test files always run, so their lines would pad the number.
exclude_args() {
  local globs
  globs="$(gate_setting exclude)"
  [[ -z "$globs" ]] && return 0
  printf -- '--exclude %s' "$globs"
}

if [[ $FAST -eq 0 ]]; then
  if [[ $FRESH -eq 1 ]]; then
    rm -rf mutants
  fi
  if gate_runs patch-coverage; then
    set -f
    # shellcheck disable=SC2046,SC2086  # the exclude list is split on purpose, and not globbed
    uv run --with-requirements scripts/gate-requirements.txt diff-cover coverage.xml --compare-branch "$BASE" \
      --fail-under "$(gate_setting threshold)" $(exclude_args)
    set +f
  fi
  if gate_runs bdd; then
    paths="$(gate_setting paths)"
    threshold="$(gate_setting threshold)"
    # shellcheck disable=SC2086  # paths is a space-separated list
    uv run --with-requirements scripts/gate-requirements.txt pytest $paths --cov --cov-report=xml:coverage-bdd.xml
    set -f
    # shellcheck disable=SC2046,SC2086  # the exclude list is split on purpose, and not globbed
    uv run --with-requirements scripts/gate-requirements.txt diff-cover coverage-bdd.xml --compare-branch "$BASE" \
      --fail-under "$threshold" $(exclude_args)
    set +f
  fi
  changed_python=$(git diff --name-only "$BASE"...HEAD -- '*.py' || true)
  if gate_runs mutation; then
    if [[ "$MUTATION" == on || -n "$changed_python" ]]; then
      threshold="$(gate_setting threshold)"
      improvement="$(gate_setting improvement)"
      uv run --with-requirements scripts/gate-requirements.txt python scripts/mutation_plan.py run --base "$BASE"
      uv run --with-requirements scripts/gate-requirements.txt python scripts/check_mutation_ratchet.py --base "$BASE" \
        --threshold "$threshold" --improvement "$improvement"
    else
      echo "mutation ratchet: skipped (no Python production or test changes)"
    fi
  fi
fi

echo "--- thresholds loosened (advisory; a person decides) ---"
uv run --with-requirements scripts/gate-requirements.txt python scripts/config_loosening.py --base "$BASE"
echo "--- design review (advisory; nothing here fails the run) ---"
uv run --with-requirements scripts/gate-requirements.txt python scripts/design_review.py --base "$BASE"
uv run --with-requirements scripts/gate-requirements.txt python scripts/craftcov_pr_comment.py --base "$BASE" --dry-run > craftcov-report.md
uv run --with-requirements scripts/gate-requirements.txt python scripts/craftcov.py --format sarif --no-cache --no-diff > craftcov.sarif
