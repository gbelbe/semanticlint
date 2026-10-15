#!/usr/bin/env python3
"""Plan a diff-scoped mutation run: drop only the cached verdicts a change can have staled.

`mutmut run` already re-tests a production function whose source hash changed. What it cannot see is
everything else that decides a verdict: a test that was edited, a fixture or helper those tests
import,
a data file they read, an unmutated module a mutated function calls. Its only answer to those is the
blunt one (`on_dependency_change = "rerun"`): reset every verdict and rerun the whole campaign —
minutes
spent re-proving functions the change cannot have touched.

This script turns the diff into the narrowest set of cached verdicts to drop, then lets an ordinary
`mutmut run` re-test exactly those (it re-tests every mutant whose verdict is empty):

    mutation_plan.py run --base origin/main      # plan, drop, `mutmut run`, repeat once if needed
    mutation_plan.py plan --base origin/main     # read-only: what would be dropped, and why

The first initialisation of a repo (no `mutants/` cache), and the few causes that really are
cache-wide
(a lock file, the dependency list, pytest's own arguments, the root conftest), still run in full.
Pair it with `on_dependency_change = "warn"` and no `tests/**/*.py` in
`cache_invalidation_files`, or
mutmut's own invalidation resets everything before this script has a say.

It reads and rewrites mutmut 3.8's `mutants/` files (the `.meta` verdicts, `mutmut-stats.json`).
That is
the same kind of coupling `check_mutation_ratchet.py` already accepts; every assumption about
the format
is checked before use and a mismatch falls back to a full run rather than a wrong incremental one.

Usage:
    python scripts/mutation_plan.py plan  [--base origin/main] [--path .] [--json]
    python scripts/mutation_plan.py apply [--base origin/main] [--path .]
    python scripts/mutation_plan.py run   [--base origin/main] [--path .]
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent)
)  # siblings by bare name, also when imported as scripts.<name>
from gate_timing import step  # noqa: E402

try:  # Python 3.11+; older interpreters fall back to a full run rather than guessing
    import tomllib
except ImportError:  # pragma: no cover - exercised only on 3.10
    tomllib = None  # type: ignore[assignment]

# A change to any of these can alter every verdict: rerun everything.
FULL_RERUN_FILES = (
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "requirements*.txt",
    "setup.py",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
)
FULL_RERUN_SECTIONS = (
    "project.dependencies",
    "project.optional-dependencies",
    "build-system",
    "tool.pytest",
    "tool.mutmut.pytest_add_cli_args",
)
_RENAME_PATHS = 2  # `git diff --name-status` names a rename as old<TAB>new
_PASSES = 2  # plan and run once, and once more when new tests had to be measured first
_SELECTION_KEY = "tool.mutmut.pytest_add_cli_args_test_selection"


@dataclass(frozen=True)
class Selection:
    """The test files in mutmut's selection, now and at the base ref."""

    now: tuple[str, ...]
    before: tuple[str, ...]


@dataclass(frozen=True)
class ImportGraph:
    """Who imports whom among the repo's own modules, and what each selected test file imports."""

    imports: dict[str, set[str]] = field(default_factory=dict)  # module -> repo modules it imports
    tests: dict[str, set[str]] = field(default_factory=dict)  # test file -> modules it imports


@dataclass(frozen=True)
class Inputs:
    """Everything the decision needs, gathered up front so the decision itself does no I/O."""

    changes: tuple[tuple[str, str], ...]  # (status A/M/D, repo-relative path)
    mutated_files: frozenset[str]  # files mutmut mutates
    selection: Selection
    stats: dict | None  # mutants/mutmut-stats.json, None when there is no cache
    sources: dict[str, str] = field(default_factory=dict)  # path -> text, tests and mutated files
    changed_sections: tuple[str, ...] = ()  # pyproject sections that differ from the base
    graph: ImportGraph = field(default_factory=ImportGraph)


@dataclass(frozen=True)
class Plan:
    mode: str  # "init" (no cache), "full" (cache-wide cause) or "incremental"
    reasons: tuple[str, ...] = ()
    reset_functions: tuple[str, ...] = ()  # mutmut's mangled names whose verdicts are dropped
    stale_tests: tuple[str, ...] = ()  # test ids whose coverage must be collected again
    selection_added: tuple[str, ...] = ()
    needs_second_pass: bool = (
        False  # new tests: their coverage is only known after one `mutmut run`
    )


# ── the decision ────────────────────────────────────────────────────────────────────────────────


def plan(inputs: Inputs) -> Plan:
    if inputs.stats is None:
        return Plan("init", ("no mutation cache: first initialisation",))
    full = _full_rerun_reasons(inputs)
    if full:
        return Plan("full", tuple(full))
    return _incremental(inputs)


def _full_rerun_reasons(inputs: Inputs) -> list[str]:
    reasons = []
    for _status, path in inputs.changes:
        name = path.rsplit("/", 1)[-1]
        if any(fnmatch.fnmatch(name, pattern) for pattern in FULL_RERUN_FILES):
            reasons.append(f"{path} changed: it can alter any verdict")
        if path in ("conftest.py", "tests/conftest.py"):
            reasons.append(f"{path} changed: it applies to every test")
    reasons += [
        f"{section} changed in pyproject.toml: it can alter any verdict"
        for section in inputs.changed_sections
        if section in FULL_RERUN_SECTIONS
    ]
    return reasons


@dataclass
class _Domain:
    """What the changes so far have staled: the tests to re-measure, and why."""

    reasons: list[str] = field(default_factory=list)
    stale: set[str] = field(default_factory=set)
    second_pass: bool = False

    def add(self, tests: set[str], why: str) -> None:
        if tests:
            self.stale.update(tests)
            self.reasons.append(why)


@dataclass(frozen=True)
class _Context:
    inputs: Inputs
    known_tests: set[str]
    selected: set[str]
    removed: set[str]

    def tests_in(self, prefixes: tuple[str, ...]) -> set[str]:
        return {t for t in self.known_tests if t.startswith(prefixes)}


def _incremental(inputs: Inputs) -> Plan:
    stats = inputs.stats or {}
    by_function: dict[str, list[str]] = stats.get("tests_by_mangled_function_name", {})
    known = set(stats.get("duration_by_test", {})).union(*map(set, by_function.values()))
    selected = set(inputs.selection.now)
    removed = set(inputs.selection.before) - selected
    added = tuple(sorted(selected - set(inputs.selection.before)))
    ctx = _Context(inputs, known, selected, removed)

    domain = _Domain()
    domain.add(ctx.tests_in(tuple(f"{f}::" for f in removed)), "left the mutation selection")
    for status, path in inputs.changes:
        _classify(ctx, status, path, domain)

    reset = _functions_covered_by(by_function, domain.stale)
    reset |= _functions_reading_data(inputs, by_function)
    return Plan(
        "incremental",
        tuple(domain.reasons),
        tuple(sorted(reset)),
        tuple(sorted(domain.stale)),
        added,
        domain.second_pass or bool(added),
    )


def _classify(ctx: _Context, status: str, path: str, domain: _Domain) -> None:
    """Add to *domain* whatever the change to *path* can have staled."""
    if path in ctx.selected or path in ctx.removed:
        tests = ctx.tests_in((f"{path}::",))
        if status == "A" and not tests:
            domain.second_pass = True  # new tests: nothing to reset until mutmut has measured them
            domain.reasons.append(f"{path} is new: its coverage is collected on the next run")
        else:
            domain.add(tests, f"{path} {_verb(status)}")
    elif path.startswith("tests/"):
        domain.add(
            _support_tests(ctx.inputs, path, ctx.known_tests), f"{path} changed (test support)"
        )
    elif path.endswith(".py") and path not in ctx.inputs.mutated_files:
        stale = _dependent_tests(ctx.inputs, path, ctx.known_tests)
        domain.add(stale, f"{path} changed (unmutated module)")
    # a mutated file is left to mutmut, which hashes its functions itself


def _verb(status: str) -> str:
    return {"D": "was deleted", "A": "was added"}.get(status, "changed")


def _functions_covered_by(by_function: dict[str, list[str]], tests: set[str]) -> set[str]:
    return {fn for fn, covering in by_function.items() if tests.intersection(covering)}


def _support_tests(inputs: Inputs, path: str, known_tests: set[str]) -> set[str]:
    """The tests a changed file under tests/ can affect: a conftest's subtree, a helper's importers,
    a data file's readers, else the tests nearest it."""
    name = path.rsplit("/", 1)[-1]
    directory = path.rsplit("/", 1)[0] if "/" in path else ""
    if name == "conftest.py":
        return {t for t in known_tests if t.startswith(f"{directory}/")}
    if name.endswith(".py"):
        files = _files_importing(inputs, path)
    else:
        files = {f for f in inputs.selection.now if name in inputs.sources.get(f, "")}
        files = files or _nearest_test_files(inputs, directory)
    return {t for t in known_tests if t.split("::", 1)[0] in files}


def _files_importing(inputs: Inputs, path: str) -> set[str]:
    stem = path.rsplit("/", 1)[-1][: -len(".py")]
    dotted = path[: -len(".py")].replace("/", ".")
    found = set()
    for test_file in inputs.selection.now:
        for module in _imported_names(inputs.sources.get(test_file, "")):
            if module in (stem, dotted) or module.endswith(f".{stem}"):
                found.add(test_file)
    return found


def _imported_names(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def _nearest_test_files(inputs: Inputs, directory: str) -> set[str]:
    parts = directory.split("/")
    for depth in range(len(parts), 0, -1):
        prefix = "/".join(parts[:depth]) + "/"
        near = {f for f in inputs.selection.now if f.startswith(prefix)}
        if near:
            return near
    return set(inputs.selection.now)


def _module_of(path: str) -> str:
    dotted = path[: -len(".py")].replace("/", ".")
    return dotted[: -len(".__init__")] if dotted.endswith(".__init__") else dotted


def _dependent_tests(inputs: Inputs, path: str, known_tests: set[str]) -> set[str]:
    """Tests whose imports lead, directly or not, to the changed unmutated module."""
    reverse: dict[str, set[str]] = {}
    for module, imported in inputs.graph.imports.items():
        for target in imported:
            reverse.setdefault(target, set()).add(module)
    start = _module_of(path)
    reached, queue = {start}, deque([start])
    while queue:
        for importer in reverse.get(queue.popleft(), ()):
            if importer not in reached:
                reached.add(importer)
                queue.append(importer)
    files = {f for f, modules in inputs.graph.tests.items() if reached & modules}
    return {t for t in known_tests if t.split("::", 1)[0] in files}


def _functions_reading_data(inputs: Inputs, by_function: dict[str, list[str]]) -> set[str]:
    """Every function of a mutated module that names a changed non-Python source-tree file."""
    roots = {f.split("/", 1)[0] for f in inputs.mutated_files}
    names = [
        path.rsplit("/", 1)[-1]
        for _status, path in inputs.changes
        if not path.endswith((".py", ".md")) and path.split("/", 1)[0] in roots
    ]
    modules = {
        _module_of(f)
        for f in inputs.mutated_files
        if any(n in inputs.sources.get(f, "") for n in names)
    }
    return {fn for fn in by_function if split_mangled(fn)[0] in modules}


# ── mutmut's file formats ───────────────────────────────────────────────────────────────────────


def split_mangled(mangled: str) -> tuple[str, str]:
    """'pkg.mod.x_load' -> ('pkg.mod', 'x_load'); class methods are 'pkg.mod.xǁClassǁmethod'."""
    cut = max(mangled.rfind(".x_"), mangled.rfind(".xǁ"))
    return (mangled[:cut], mangled[cut + 1 :]) if cut >= 0 else (mangled, "")


def reset_verdicts(meta: dict, mangled_functions: set[str]) -> int:
    """Empty the cached verdict of each mutant of *mangled_functions*; mutmut re-tests those."""
    codes = meta.get("exit_code_by_key", {})
    prefixes = tuple(f"{fn}__mutmut_" for fn in mangled_functions)
    count = 0
    for key in codes:
        if key.startswith(prefixes) and codes[key] is not None:
            codes[key] = None
            count += 1
    return count


def drop_tests(stats: dict, tests: set[str]) -> None:
    """Forget these tests: with no duration on record, mutmut measures them again as new."""
    for test in tests:
        stats.get("duration_by_test", {}).pop(test, None)
    by_function = stats.get("tests_by_mangled_function_name", {})
    for function, covering in by_function.items():
        by_function[function] = [t for t in covering if t not in tests]


def selection_fingerprint(values: list[str] | tuple[str, ...]) -> str:
    """mutmut 3.8's fingerprint of the test-selection arguments (configuration.py, `_hash`)."""
    return hashlib.sha256(repr(tuple(values)).encode()).hexdigest()[:12]


# ── gathering the inputs ────────────────────────────────────────────────────────────────────────


def _git(root: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout if out.returncode == 0 else ""


def read_changes(root: Path, base: str) -> tuple[tuple[str, str], ...]:
    changes = []
    for line in _git(root, "diff", "--name-status", "-M", base, "--").splitlines():
        status, *paths = line.split("\t")
        if status.startswith("R") and len(paths) == _RENAME_PATHS:
            changes += [("D", paths[0]), ("A", paths[1])]
        elif paths:
            changes.append((status[0], paths[0]))
    # a file not yet added to git is a change too (locally; in CI everything is committed)
    seen = {path for _status, path in changes}
    changes += [
        ("A", p)
        for p in _git(root, "ls-files", "--others", "--exclude-standard").splitlines()
        if p not in seen
    ]
    return tuple(changes)


def _pyproject(text: str) -> dict:
    if tomllib is None or not text:
        return {}
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}


def _lookup(doc: dict, dotted: str):
    for part in dotted.split("."):
        if not isinstance(doc, dict) or part not in doc:
            return None
        doc = doc[part]
    return doc


def changed_sections(old: dict, new: dict) -> tuple[str, ...]:
    watched = (*FULL_RERUN_SECTIONS, _SELECTION_KEY)
    return tuple(s for s in watched if _lookup(old, s) != _lookup(new, s))


def selection_files(doc: dict) -> tuple[str, ...]:
    args = _lookup(doc, _SELECTION_KEY) or []
    return tuple(a for a in args if isinstance(a, str) and a.endswith(".py"))


def _repo_python_files(root: Path) -> list[str]:
    listed = _git(root, "ls-files", "*.py").splitlines()
    return [p for p in listed if not p.startswith(("mutants/", ".venv/"))]


def _resolve(module: str | None, level: int, current: str, is_package: bool) -> str | None:
    if level == 0:
        return module
    parts = current.split(".")
    base = parts if is_package else parts[:-1]
    base = base[: len(base) - (level - 1)] if level > 1 else base
    return ".".join([*base, module] if module else base) or None


def import_graph(root: Path, files: list[str]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """module -> repo modules it imports, and test file -> repo modules it imports."""
    modules = {_module_of(f): f for f in files}
    graph: dict[str, set[str]] = {}
    by_file: dict[str, set[str]] = {}
    for module, rel in modules.items():
        try:
            tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        package = rel.endswith("__init__.py")
        found: set[str] = set()
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = _resolve(node.module, node.level, module, package)
                if base:
                    names = [base, *(f"{base}.{a.name}" for a in node.names)]
            found.update(n for n in names if n in modules)
        graph[module] = found
        by_file[rel] = found
    return graph, by_file


def collect_inputs(root: Path, base: str, mutants_dir: Path) -> tuple[Inputs, list[str], list[str]]:
    new_doc = _pyproject(
        (root / "pyproject.toml").read_text() if (root / "pyproject.toml").exists() else ""
    )
    old_doc = _pyproject(_git(root, "show", f"{base}:pyproject.toml"))
    mutate = _lookup(new_doc, "tool.mutmut.only_mutate") or []
    files = _repo_python_files(root)
    mutated = frozenset(f for f in files if any(fnmatch.fnmatch(f, p) for p in mutate))
    selection = selection_files(new_doc)
    wanted = {*selection, *selection_files(old_doc), *mutated}
    sources = {}
    for rel in wanted:
        try:
            sources[rel] = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    stats_path = mutants_dir / "mutmut-stats.json"
    try:
        stats = json.loads(stats_path.read_text())
    except (OSError, json.JSONDecodeError):
        stats = None
    graph, by_file = import_graph(root, files)
    inputs = Inputs(
        changes=read_changes(root, base),
        mutated_files=mutated,
        selection=Selection(selection, selection_files(old_doc) if old_doc else selection),
        stats=stats,
        sources=sources,
        changed_sections=changed_sections(old_doc, new_doc) if old_doc else (),
        graph=ImportGraph(graph, {f: by_file.get(f, set()) for f in selection}),
    )
    return (
        inputs,
        list(_lookup(old_doc, _SELECTION_KEY) or []),
        list(_lookup(new_doc, _SELECTION_KEY) or []),
    )


# ── applying a plan ─────────────────────────────────────────────────────────────────────────────


class CacheFormatError(Exception):
    """The cache does not look like the mutmut version this script was written against."""


def resign_selection(stats: dict, old_args: list[str], new_args: list[str]) -> None:
    """Make mutmut see the test selection as unchanged when the files it adds have simply not been
    measured yet; it would otherwise reset every verdict.

    The cache was built from some earlier selection, which is not necessarily the base ref's.
    Two candidates are tried: the base ref's, and the current one without the files the cache has
    no test from. The stored fingerprint must match one of them exactly, or the format is not what
    this script knows and the caller runs in full.
    """
    fingerprint = stats.setdefault("config_fingerprint", {})
    stored = fingerprint.get("test_selection")
    wanted = selection_fingerprint(new_args)
    if stored == wanted:
        return
    measured = {test.split("::", 1)[0] for test in stats.get("duration_by_test", {})}
    unmeasured = {a for a in new_args if a.endswith(".py") and a not in measured}
    candidates = (old_args, [a for a in new_args if a not in unmeasured])
    if not any(selection_fingerprint(candidate) == stored for candidate in candidates):
        raise CacheFormatError("the stored test-selection fingerprint matches no known selection")
    fingerprint["test_selection"] = wanted


def apply(plan_: Plan, mutants_dir: Path, old_args: list[str], new_args: list[str]) -> int:
    """Drop the planned verdicts and stale tests; returns how many mutant verdicts were dropped."""
    stats_path = mutants_dir / "mutmut-stats.json"
    stats = json.loads(stats_path.read_text())
    resign_selection(stats, old_args, new_args)
    drop_tests(stats, set(plan_.stale_tests))
    stats_path.write_text(json.dumps(stats, indent=4))

    by_module: dict[str, set[str]] = {}
    for function in plan_.reset_functions:
        module, _ = split_mangled(function)
        by_module.setdefault(module, set()).add(function)
    dropped = 0
    for module, functions in by_module.items():
        meta_path = mutants_dir / (module.replace(".", "/") + ".py.meta")
        if not meta_path.exists():
            meta_path = mutants_dir / (module.replace(".", "/") + "/__init__.py.meta")
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        dropped += reset_verdicts(meta, functions)
        meta_path.write_text(json.dumps(meta, indent=4))
    return dropped


def record_domain(mutants_dir: Path, functions: tuple[str, ...], *, fresh: bool) -> None:
    """Write the functions re-tested for this change where the ratchet looks for them.

    *fresh* starts the record over (first pass of a run); otherwise it is added to, so the second
    pass of a run keeps what the first one reset. A cache restored from an earlier run must not
    carry its list over.
    """
    path = mutants_dir / "mutation-plan.json"
    previous: list[str] = []
    if not fresh and path.exists():
        try:
            previous = json.loads(path.read_text()).get("reset_functions", [])
        except json.JSONDecodeError:
            previous = []
    mutants_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"reset_functions": sorted({*previous, *functions})}, indent=2))


def _mutmut_run(root: Path) -> int:
    return subprocess.run([sys.executable, "-m", "mutmut", "run"], cwd=root, check=False).returncode


def _prepare(root: Path, base: str, mutants_dir: Path, attempt: int) -> Plan:
    """Decide, then leave the cache ready for a plain `mutmut run`."""
    with step("mutation plan: read the repo and decide"):
        inputs, old_args, new_args = collect_inputs(root, base, mutants_dir)
        decided = plan(inputs)
    print(summary(decided))
    with step(f"mutation plan: prepare the cache ({decided.mode})"):
        if decided.mode == "full" and mutants_dir.exists():
            shutil.rmtree(mutants_dir)
        elif decided.mode == "incremental":
            dropped = apply(decided, mutants_dir, old_args, new_args)
            print(f"dropped {dropped} cached verdict(s)")
            record_domain(mutants_dir, decided.reset_functions, fresh=attempt == 1)
    return decided


def run(root: Path, base: str, mutants_dir: Path) -> int:
    """Plan, drop, `mutmut run`; once more when new tests had to be measured first.

    Anything unexpected in planning falls back to the campaign mutmut would have run anyway: a
    wrong plan must cost time, never a wrong verdict.
    """
    for attempt in range(1, _PASSES + 1):
        try:
            decided = _prepare(root, base, mutants_dir, attempt)
        except Exception as exc:  # noqa: BLE001 - any failure here means "run in full"
            print(f"mutation plan failed ({exc!r}): running in full", file=sys.stderr)
            shutil.rmtree(mutants_dir, ignore_errors=True)
            return _mutmut_run(root)
        with step(f"mutmut run (pass {attempt})"):
            code = _mutmut_run(root)
        if code != 0 or not decided.needs_second_pass or attempt == _PASSES:
            return code
    return 0


def summary(decided: Plan) -> str:
    lines = [f"mutation plan: {decided.mode}"]
    lines += [f"  - {reason}" for reason in decided.reasons]
    if decided.mode == "incremental":
        lines.append(
            f"  {len(decided.reset_functions)} function(s) to re-test, "
            f"{len(decided.stale_tests)} test(s) to re-measure"
        )
        if decided.selection_added:
            lines.append(f"  new test file(s): {', '.join(decided.selection_added)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=("plan", "apply", "run"))
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--path", default=".")
    parser.add_argument("--mutants-dir", default="mutants")
    parser.add_argument("--json", action="store_true", help="plan: print the plan as JSON")
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    mutants_dir = root / args.mutants_dir
    if args.command == "run":
        return run(root, args.base, mutants_dir)
    inputs, old_args, new_args = collect_inputs(root, args.base, mutants_dir)
    decided = plan(inputs)
    if args.command == "plan":
        if args.json:
            print(json.dumps(decided.__dict__, indent=2))
        else:
            print(summary(decided))
        return 0
    print(summary(decided))
    if decided.mode == "incremental":
        print(f"dropped {apply(decided, mutants_dir, old_args, new_args)} cached verdict(s)")
        record_domain(mutants_dir, decided.reset_functions, fresh=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
