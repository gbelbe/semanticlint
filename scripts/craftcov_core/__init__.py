"""craftCov — a coverage-report-style scan of the craftsmanship catalog.

The implementation lives in this package, one module per concern (catalog, file
discovery, scope attribution, detector adapters, the dupes engine, scanning, the
cache, summaries, rendering, the pipeline and the CLI); scripts/craftcov.py is the
entry point and a facade re-exporting the names other scripts import.

Honest about its limits before anything else: only the entries in
catalog.yaml that carry `detectors` (8 of 35 as of this writing — see
`--list-detectors`) have a real mechanical proxy here. Four more
(cyclomatic/cognitive complexity, invariant return, duplicated literal)
are covered by a separate script, `check_complexity_ratchet.py` — this
module has no awareness of it, so they show as "needs judgment" below even
though they are, in fact, mechanically checked elsewhere; see
CRAFTSMANSHIP.md's "The complexity ratchet". Three engines reused, one
technique ported rather than reimplemented from scratch:

  - `ruff` (Rust, already a dependency in every repo this ships to, ships
    its own fast internal cache) — guard-clauses, dead-code,
    explaining-constant, extract-helper, introduce-parameter-object,
    replace-conditional-with-polymorphism.
  - `pylint`, scoped to exactly two rules (R0902/R0904) — extract-class /
    God Class. ruff hasn't ported these yet (R0904 is preview-only there,
    R0902 doesn't exist in ruff at all); upstream pylint's originals are
    stable, so this is the one entry that needs a second tool on PATH.
  - `vulture` — a second, higher-recall pass for dead-code alongside
    ruff's F401/F811/F841: catches unused module-level functions/classes
    ruff's own-file-scoped checks can't see. Verified on a real, framework-
    heavy codebase (kai-ster: pytest-bdd + Textual) while building this:
    vulture's confidence scores cluster hard into two tiers — unused
    *variables* at 100% (redundant with ruff's own F841, adds nothing) and
    unused functions/classes/methods at 60% (vulture's own "fairly sure but
    could be wrong" floor — decorator-registered step defs and Textual's
    on_* handlers score exactly here without being genuinely dead). That
    60% tier is also where all of vulture's actual unique value lives, so
    craftCov reports it unfiltered by default (`--vulture-min-confidence 0`,
    vulture's own default) rather than quietly discarding the one thing
    ruff can't already tell you — raise the threshold yourself via
    `--vulture-min-confidence` once you've triaged a first pass and know
    your codebase's noise floor. The per-finding confidence is preserved in
    `--verbose`/JSON output for exactly this triage.
  - `dupes` (this module's own code, not a subprocess) — a from-scratch
    port of the rolling-hash line-window matching technique both PMD CPD
    (Karp-Rabin string matching over a token stream, per PMD's own docs)
    and pylint's own R0801 checker (same technique, one level coarser:
    stripped lines instead of language tokens — verified against pylint's
    actual source before porting) use — consolidate-duplicate-conditional.
    Ported rather than subprocessing pylint's checker because its CLI only
    puts ONE of a duplicate pair's two locations in structured JSON output
    (the other is free text inside the message), and its internal API is
    private/unstable across versions. See that section of this file for
    the full explanation, including why it's corpus-wide (runs over every
    file, every time — never through the per-file cache, unlike the three
    subprocess engines above) and what "exact match, no docstring
    special-casing" means for it in practice.

Feature Envy, Data Clumps *precisely* (not just "too many params" — the
*same group* repeating), Message Chains, Primitive Obsession, Refused
Bequest, and every `principle`/`workflow` entry have no detector on
purpose: no maintained, reusable Python tool exists for any of them
(checked against the design-smell-detection literature, which is
Java/C#/C++-tooling-only). A regex or AST check confident enough to report
these would cry wolf more than it'd help. Those stay a job for the
procedure in CRAFTSMANSHIP.md (read the code, ask the developer), not this
script. craftCov finds the mechanically-checkable subset; it is not a
replacement for the judgment call the rest of the catalog asks for.

Caching: findings for a file are cached by its content hash, keyed by path
relative to the scan root (so the cache survives the repo moving to a
different absolute path). A re-run only re-scans files whose hash changed
since the last run (or that are new); everything else is read back from
`.craftcov_cache.json`. This is on top of, not instead of, each tool's own
cache where it has one (ruff's `.ruff_cache/`) — craftCov's cache also
stores the class/function attribution none of the three tools track on
their own, so a warm re-run skips re-parsing ASTs too, not just re-linting.

When more than one tool flags the *same* line for the *same* heuristic
(e.g. ruff's F401 and vulture both catch an unused import), it's counted
once, not twice — see `scan_files`'s dedup.

Requires (unlike the other craft-gate scripts, which are plain bash):
PyYAML importable, plus whichever of `ruff` / `pylint` / `vulture` is on
PATH for the detectors catalog.yaml actually uses — only invoked if at
least one entry needs it, so a repo without pylint installed still gets
the other engines' findings, not a hard failure. `dupes` needs nothing
beyond the stdlib. `uv sync --extra craftcov` in this repo installs all
three external engines; see README's Requirements.

Usage:
    python3 scripts/craftcov.py                  # scan, text report
    python3 scripts/craftcov.py --format json     # machine-readable
    python3 scripts/craftcov.py --verbose         # + every finding, file:line
    python3 scripts/craftcov.py --no-cache        # ignore and overwrite the cache
    python3 scripts/craftcov.py --list-detectors  # which heuristics are detectable, and how
"""
