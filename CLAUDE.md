# semanticlint — Claude Code guidelines

## Code quality gate (mandatory before every commit)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/semanticlint/
uv run pytest tests/ -q
```

Run `uv run ruff check --fix . && uv run ruff format .` to auto-fix most lint/format issues.

## Ruff rules to follow in new code

| Rule  | Pattern to avoid                          | Correct pattern                                      |
|-------|-------------------------------------------|------------------------------------------------------|
| I001  | Unsorted imports                          | stdlib → third-party → local, blank lines between   |
| F401  | Unused import                             | Remove it entirely                                   |
| UP037 | `"quoted"` type annotation                | Unquoted + `from __future__ import annotations`      |
| SIM103| `if cond: return False; return True`      | `return not cond`                                    |
| B905  | `zip(a, b)` without `strict=`             | `zip(a, b, strict=False)` or `strict=True`           |

## Mypy rules to follow in new code

- `str | None` passed where `str` expected → add `assert x is not None` before the call
- Variable re-defined in separate `elif` branches → add `# type: ignore[no-redef]`
- Private attr on third-party type → add `# type: ignore[attr-defined]`
- Every new `.py` file must start with `from __future__ import annotations`

## Tidy First & craftsmanship (mandatory before every feature/fix commit)

Before writing a feature or fix, check the file(s)/function(s)/class(es) it
touches against the catalog in **`CRAFTSMANSHIP.md`** (Kent Beck's *Tidy
First?*, Fowler's *Refactoring* smells, *Clean Code*, and Feathers'
legacy-code method — see also the `tidy-first` skill, which is a thin
wrapper around that same file). If a tidying applies, do it alone, verify
the suite is unchanged, and commit it separately, naming the source:

```
tidy(<type>): <what and where>

Tidy-Type: <type>
Tidy-Source: <author, book>
```

Only then commit the feature/fix. If nothing applies, don't invent one —
commit with a `Tidy-Exempt: <reason>` trailer instead.

The `tidy-ratchet` check (`scripts/check_tidy_ratchet.sh`, pre-push hook + CI)
fails a push/PR with no `tidy(...)` commit, no `test(characterize):` commit,
and no `Tidy-Exempt:` trailer in range. It's a text check on commit messages
only, so it costs milliseconds; it cannot judge whether the right tidying
was picked.

For the 8 catalog heuristics craftCov can detect mechanically (`uv run
scripts/craftcov.py --list-detectors`), skip the judgment call: `uv run
scripts/craftcov.py --file <path>` before touching a file, fix one instance
of every heuristic it finds present, bundle it all into one `tidy(multi):`
commit (see `CRAFTSMANSHIP.md`'s "Refactor First"). CI's `refactor-first` job
(`scripts/check_refactor_first.py`) enforces the *outcome* — a touched
file's total across those heuristics must go down, or stay at 0 —
`Tidy-Exempt:` bypasses it the same way it bypasses the ratchet above.

The catalog is also a checklist for **new** code, not just a pre-touch
ritual: Beck's four rules of simple design (pass the tests, reveal intention,
no duplication, fewest elements) and Clean Code's function-size/SOLID
principles are the acceptance bar for anything written from scratch — there's
nothing to "tidy" in code that doesn't exist yet, but there's everything to
get right the first time.

Touching code with no tests? It's legacy by Feathers' definition regardless
of age — write a `test(characterize):` commit pinning its current behavior
first, *then* tidy under that safety net. See `CRAFTSMANSHIP.md`'s "Working
with legacy code."

## TDD + BDD workflow (mandatory)

This project follows strict TDD with BDD for behaviour specification.

**Before writing any implementation code for a new feature, you MUST:**

1. Write the Gherkin `.feature` file under `tests/features/`
2. List every unit test case — happy path, edge cases, error paths
3. Show which files will receive them and the function names
4. Wait for explicit user confirmation

**Only after approval:**
- Write the `pytest-bdd` step definitions under `tests/step_defs/`
- Write the unit tests under `tests/unit/`
- Write the implementation

## BDD conventions

- Feature files live in `tests/features/<domain>/` (e.g. `lint/`, `skos/`, `detect/`)
- Step definitions live in `tests/step_defs/test_<domain>.py`
- One `.feature` file per check domain
- Scenario names must be human-readable business descriptions, not technical descriptions
- Use `@pytest.fixture` for shared RDF graph setup (avoid duplication across step files)

## Project conventions

- Check ID scheme: `RDF*` syntax, `SKO*` SKOS, `OWL*` OWL, `RDS*` RDFS, `QUA*` quality, `CUS*` custom
- Every check is a class decorated with `@CheckRegistry.register`
- `applies_to: VocabType` flag determines which vocab types trigger the check
- `Violation.subject` should always point to the offending RDF node when available
- All new checks need both unit tests AND a BDD scenario
