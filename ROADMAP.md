# Roadmap

semanticlint is evolving from a set of hand-written checks into an **aggregation
layer over [pySHACL](https://github.com/RDFLib/pySHACL)**: SHACL expresses the
per-node constraints (the standard, reusable way), while semanticlint adds what
SHACL cannot — aggregate quality gates, hierarchy-scoped metrics, curated rule
sets, and a layered configuration system — behind one severity-graded report.

See `docs/architecture/layered-rules.md` for the configuration architecture and
`README.md` (§ *Why semanticlint … SHACL / pySHACL*) for the positioning.

---

## Phase A — SHACL foundation + cardinality migration ✅

Integrate pySHACL and move the pure "must exist" constraints to SHACL shapes.

- `semanticlint/shacl/` — shapes + a runner that validates once via pySHACL and
  maps results back to `Violation`s (`slint:checkId` / `slint:appliesTo`).
- `pipeline.check_graph()` — SHACL pass + remaining Python checks, `select`/`ignore`
  applied uniformly; the CLI delegates to it.
- Migrated to shapes: **property domain**, **property range**, **class label**,
  **concept prefLabel** (identical ids, messages, severities, vocab gating).
- Kept in Python: individual-typing, undeclared-superclass, SKOS duplicate/disjoint
  labels, hierarchy cycles/orphans, URI lexical checks.

## Phase B — config-driven & value-shape migrations

Migrate the remaining checks that SHACL expresses **beyond plain cardinality**, and
introduce **config-driven shape generation**.

- **Language coverage** → shapes generated *per required language* from config
  (`sh:qualifiedValueShape` + `sh:languageIn`). Establishes config → shape
  generation (headline capability).
- **Untyped individual**, **undeclared superclass** → value/qualified shapes
  (`sh:qualifiedMinCount` + `sh:not`/`sh:in`; `sh:node` value shapes). Runner gains
  `sh:value` → message enrichment for exact parity.
- Deferred to a later SHACL-SPARQL pass (cross-property correlation): top-concept ↔
  scheme alignment. Aggregate coverage checks move to Phase D.

## Phase C — layered rules & discovery

The configuration architecture in `docs/architecture/layered-rules.md`. Turns the
existing shapes + thresholds into a **3-layer, keyed-merge** system and adds
ontology-specific local rules.

**Phase C.0 — local shape discovery (lean slice) ✅ done.** Auto-discover
`*.shapes.ttl` next to the ontology and union it into validation: business rules
are enforced and gate CI with zero wiring, keyed by `slint:checkId` or the shape
name; shapes files are excluded from data. Ships ahead of the full layered config
so business rules are usable now. The remaining bullets (global layer, keyed
override/merge, provenance command) are deferred until overrides are actually
needed.

- **Layers**: defaults → `~/.config/semanticlint/config.yml` (global) → local
  (`onto-ci.yml` + shapes files versioned with the ontology); most-local wins.
- **Discovery (both)**: convention (`*.shapes.ttl` sibling / `.semanticlint/`) +
  explicit (`shapes:` glob in `onto-ci.yml`), via an EditorConfig-style upward walk
  stopping at `root: true`.
- **Keyed merge**: union by default, override on same id/key; explicit
  `select`/`ignore` (replace) vs `extend-select`/`extend-ignore` (add), and
  disable-in-place (`ignore` / `sh:deactivated`).
- **Ontology-specific constraints**: the local shapes graph is unioned in — e.g.
  "a `Person` may `work_for` at most one `Department`" lives in `zoo.shapes.ttl`.
- **Provenance**: `semanticlint config --resolved <path>` prints the effective rule
  set and each rule's origin layer (à la `git config --show-origin`).

## Phase D — quality gates & the metrics engine (deferred)

The aggregate/statistical quality SHACL cannot do — the "≥ 50% of labels" gates.
**Deferred by choice:** the four aggregate coverage gates (QUA001/002/004/005)
already work today as simple whole-graph Python checks, which is enough to "start
simple." This phase (per-subtree scope + per-level thresholds) is a non-breaking
enhancement to add if/when those richer metrics are wanted; nothing depends on it.

- `semanticlint/metrics.py` — `MetricSpec` / `MetricResult` / `evaluate_metrics`;
  the coverage checks (concept label, definition, class label, property label)
  become adapters over it.
- **Hierarchy scope** — `scope: graph | hierarchy`: aggregate per class/subtree over
  a generic subsumption hierarchy (`rdfs:subClassOf` / `skos:broader`), memoised
  descendant sets (diamond-safe).
- **Per-level thresholds** — `quality[key]` accepts a scalar (today) or
  `{ default, by_order }`, resolved through the Phase C layered config.
- Public API `evaluate_metrics(graph, config, scope)` returns every result (pass and
  fail) so consumers (e.g. ster's per-subtree "Semantic Quality Analysis" block) can
  render the full table.

## Later / deferred

- **SHACL-SPARQL pass** for cross-property correlations (top-concept ↔ scheme) and
  anything needing `GROUP BY` / property paths.
- **Consolidation & upstreaming** — retire duplicated quality logic in downstream
  tools (e.g. ster) now that semanticlint is the single source; propose a
  `scope=subjects` option upstream if the hierarchy engine proves broadly useful.
- **Org presets** — shareable global configs via `extends:`.

## Design principles

- **SHACL for per-node, Python for aggregate.** Don't force one to do the other's job.
- **Reuse linter conventions** (git / EditorConfig / Ruff / ESLint / SHACL) rather
  than inventing configuration semantics.
- **Back-compatible by default** — default scope + scalar thresholds + empty
  select/ignore reproduce current behaviour on upgrade; snapshot-tested.
- **TDD + BDD** — every phase ships its Gherkin features and unit tests first
  (see `CLAUDE.md`).
