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
