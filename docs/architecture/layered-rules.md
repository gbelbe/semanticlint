# Layered rules & configuration

How semanticlint decides *which* rules run, *where they come from*, and *who wins*
when they overlap. This is the "cascading configuration" problem that every mature
linter and test runner has solved; semanticlint follows the same well-trodden
patterns rather than inventing its own.

## Two axes, kept separate

Rules differ along two independent axes. Conflating them is the usual source of
confusion, so we name them explicitly.

### Axis 1 — the *kind* of rule (which engine runs it)

| Kind | Example | Engine |
|------|---------|--------|
| **Structural test** (per node) | "every class has an `rdfs:label`" | SHACL shape (via pySHACL) |
| **Ontology-specific constraint** (per node, domain) | "a `Person` may `work_for` at most one `Department`" | SHACL shape (authored per project) |
| **Quality gate** (aggregate threshold) | "≥ 50% of classes are labelled" | Python metrics engine |

SHACL is used for everything that is a per-node constraint; the Python metrics
engine covers aggregates/percentages, which SHACL cannot express (see
`docs/positioning-vs-shacl` and *"Is SHACL Suitable for Data Quality Assessment?"*,
arXiv 2025). The configuration system below is **engine-agnostic**: it resolves one
effective rule set, then dispatches each rule to the appropriate engine.

### Axis 2 — the *layer* a rule comes from (precedence)

Three layers, **most-local wins**, mirroring `git config` (`--system` → `--global`
→ `--local`):

1. **Defaults** — the built-in shapes, checks and default thresholds shipped with
   the installed version of semanticlint.
2. **Global config** — `~/.config/semanticlint/config.yml` (XDG). The "applies to
   every project on this install" layer. May itself `extends:` an org preset.
3. **Local (versioned with the ontology)** — discovered next to the `.ttl` files:
   - `onto-ci.yml` — thresholds, `select`/`ignore`/`extend-*`, `fail_on`;
   - one or more **SHACL shapes files** — the ontology-specific constraints,
     committed alongside the vocabulary they constrain.

Precedence: **local › global › defaults.** Where two layers touch the *same* rule,
the more-local one overrides; where they touch *different* rules, they **add up**
(union).

## Prior art (why these choices)

Every decision here has an established precedent; we deliberately reuse them so the
behaviour is unsurprising to anyone who has used a linter.

| Pattern | Established by | What we take |
|---------|----------------|--------------|
| Ordered layers, most-specific wins | **git config** (`--system/--global/--local`) | the 3-layer precedence |
| `--show-origin` (where did this come from?) | **git config** | the `--resolved` explain command |
| Walk up the tree, nearest wins, stop at a boundary | **EditorConfig** (`root = true`) | local-file discovery |
| Inherit-a-base + override | **tsconfig `extends`**, **Stylelint `extends`** | global `extends:` presets |
| **Replace vs. extend** a rule set | **Ruff** (`select`/`ignore` vs `extend-select`/`extend-ignore`) | add-up-vs-override control |
| Print the effective config | **ESLint `--print-config`**, **Ruff `--show-settings`** | the `--resolved` command |
| Rule sets union; disable one in place | **SHACL** (graph union; `sh:deactivated true`) | shape merging + per-shape disable |
| Directory-cascading extension | **pytest `conftest.py`** | local shapes accumulate up the tree |

## Discovery (convention *and* configuration — we do both)

Zero-config for the common case, explicit control when you need it:

- **Convention** — a sibling `*.shapes.ttl` next to a vocabulary file, and/or a
  `.semanticlint/` directory. Found automatically; no wiring.
- **Explicit** — a `shapes:` glob list in `onto-ci.yml`, for when shapes live
  elsewhere or must be ordered.

Resolution walks **up the directory tree** from each ontology file (EditorConfig
style), collecting every applicable `onto-ci.yml` + shapes file, and **stops at the
first `onto-ci.yml` declaring `root: true`** so configuration never leaks above the
repository. Nearer files override farther ones.

## Merge semantics — everything is *keyed*

The single mechanism behind "override on overlap, add up otherwise" is a **keyed
merge**: every rule has a stable identity, and merging is per-identity.

| Rule kind | Identity key | Add up (different keys) | Override (same key, more local) |
|-----------|--------------|-------------------------|---------------------------------|
| Threshold gate | the threshold name (`min_label_coverage`) | new keys merge in | value is replaced (per-level values arrive with the metrics engine) |
| Built-in structural check | check id (e.g. the class-label rule) | — | `ignore`/`extend-ignore` disables; `severity:` re-grades; a same-id shape replaces it |
| Ontology shape | `slint:checkId` / shape URI | new shapes union in | a local shape with the same id **replaces** the inherited one; `sh:deactivated true` turns one off |

Two footguns handled up front, both learned from Ruff/ESLint:

- **Replace vs extend is explicit.** `select`/`ignore` *replace* the inherited set;
  `extend-select`/`extend-ignore` *add* to it. A local config that just wants one
  more rule uses `extend-select` and does not silently wipe the global set.
- **Disable-in-place exists.** You can turn off a single inherited rule
  (`ignore: [ID]` or `sh:deactivated true`) without having to re-declare everything
  else — the override path, not a full replace.

## Resolution pipeline

```
effective_config  = deep_merge(defaults, global, local)         # keyed, local wins
effective_shapes  = union(default_shapes, global_shapes, local_shapes)
                    with same-id local shapes replacing earlier ones,
                    then ignore / sh:deactivated applied last
run  = pySHACL(effective_shapes) + metrics_engine(effective_config)
report(run) with per-rule provenance
```

The resolver emits, for every rule, the **layer it came from** — surfaced by:

```
semanticlint config --resolved <path>
```

which prints the effective rule set and its origins (defaults / global / local),
the semanticlint analogue of `git config --list --show-origin`. A cascading system
is undebuggable without it, so it ships with the feature, not after.

## Worked example — an ontology-specific constraint

`zoo.ttl` is committed with `zoo.shapes.ttl` beside it (auto-discovered):

```turtle
# zoo.shapes.ttl — versioned with the ontology it constrains
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix ex:    <http://example.org/zoo#> .
@prefix slint: <https://semanticlint.org/ns#> .

ex:PersonEmploymentShape a sh:NodeShape ;
    slint:checkId "ZOO001" ;
    sh:targetClass ex:Person ;
    sh:property [ sh:path ex:work_for ;
                  sh:class ex:Department ;
                  sh:maxCount 1 ;
                  sh:message "A Person may work_for at most one Department" ] .
```

No wiring: the local shape **unions** with the built-in defaults, keeps its own id
and severity, and — because it is more local — could override a same-id rule from
the global config or defaults if one existed. A reviewer sees the constraint evolve
in git next to the data it protects.

## Non-goals / notes

- **Determinism.** Layer order and same-id last-wins make resolution deterministic
  regardless of filesystem enumeration order.
- **Boundary.** `root: true` prevents configuration from leaking above the repo.
- **No new rule language.** Ontology-specific rules are plain SHACL; gates are plain
  config keys. There is nothing bespoke to learn.
