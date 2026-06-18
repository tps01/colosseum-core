# AGENTS.md

Baseline expectations for AI agents in this repository.

## Purpose

- Normative docs: `docs/scope.md`, `docs/sphinx/source/guides/`, `examples/`, and code. Bench config keys: run `python scripts/docgen/build_all.py` (generated **Bench configuration reference**). Archived ADRs/FFOs/DDDs: `docs/archive/planning/` (see `docs/archive/README.md`).
- Small, reviewable diffs. No commits unless asked. Read `RULES.md` at task start (user-owned; do not edit unless asked).

## Change discipline

Prefer **focused, compact changes** that a human can review quickly:

- Fix the root cause in the fewest files and lines that work — a 5-line targeted fix beats a 500-line refactor.
- Touch only what the task requires; leave unrelated code, style churn, and drive-by cleanups out of the diff.
- Avoid project-wide overhauls (mass renames, sweeping abstractions, new layers) unless the user explicitly asks for them.
- When several approaches exist, choose the one that is **clever but local**: e.g. a one-line CI fix, a small compat shim, or a narrow behavior change — not a new framework or cross-cutting rewrite.
- If scope grows, stop and split: land the minimal fix first; defer broader improvements to a follow-up.

Reviewability matters as much as correctness. Small diffs that are easy to read and approve are preferred over exhaustive but sprawling changes.

## API and examples

- User import: `import colosseum as col`. End-of-run: **`col.endex()`** only (flush logs/DB, `summary.txt`, `summary.json`, exit `0`/`1`). Do not gate exit via `read_verifications()` loops.
- Example/test scripts: **one line per `col.*` call** with inline keyword args (see `examples/`).
- Offline/CI bench: `examples/configs/bench.sim.toml` (`driver = "sim"`) or `COLOSSEUM_BENCH_CONFIG=bench.sim.toml`. PyVISA-sim is **test-only** (`.[test]` extra, Python 3.10+): `pytest -m visa_sim`, `examples/configs/bench.visa-sim.toml`, `bench.rf.visa-sim.toml`.

## Repository layout

| Path | Role |
|------|------|
| `colosseum/` | Core: config, context, decorators, DB, runner (`run`, `run-suite`), plugins registry |
| `colosseum_equipment/` | Plugin → `col.equipment.*` and `col.io.*` (PSU/DMM/VSG/speca/SCPI; DIO sim/FT232H + I2C/SPI stubs; `visa`/`serial`/`sim`) |
| `colosseum_shared/` | Plugin → `col.shared.*` (SSH, regex, parsing; `sim`/paramiko) |
| `colosseum_host/` | Plugin → `col.host.*` (bench PC prerequisites: system/bench/config) |
| `docs/` | Scope, testing notes, releasing; user guides are under `docs/sphinx/` |
| `docs/sphinx/source/guides/` | Hand-written Sphinx RST |
| `docs/archive/planning/` | Historical ADRs, FFOs, DDDs (not normative) |
| `outputs/` | Run artifacts (`debug.log`, `execution.sqlite`, `summary.txt`, `summary.json`) — gitignored |
| `build/` | Docgen staging + HTML — gitignored |

**Entry points:** `colosseum.plugins` (runtime `register(registry)`), `colosseum.docgen` (`docgen_entry:spec` → `DocgenModuleSpec`). Monorepo dev works without install via built-in fallbacks in `plugins/loader.py` and `docgen/discover.py`.

## Implementation status

Core runtime is implemented: single-test + suite runners, plugins, optional verifications, `summary.txt` / `summary.json`, `col.database.read_*`, vendor models `keysight-edu34450a` / `tdk-genesys`, RF VSG/speca with `keysight-esg`, `keysight-e4407b`, `tektronix-rsa5100b`. Deferred items (parallel suites, JSON-schema config, context-manager API, etc.) are listed in [`docs/scope.md`](docs/scope.md).

## Scripts

| Script | Use |
|--------|-----|
| `scripts/docgen/build_all.py` | Full Sphinx site → `build/docgen/site/html/` |
| `scripts/docgen/build_module.py` | Autodoc RST for one package |
| `scripts/cleanup.py` | Remove `outputs/`, `build/`, `__pycache__`, etc. — **`--dry-run` first** |
| `scripts/run_tests.py` | `pytest` tiers 1–3; `--regression` for soak + docgen |
| `scripts/run_static.py` | Ruff, mypy, bandit, vulture on production packages + `scripts/` (strict; CI gate) |
| `scripts/profile_unit_tests.py` | cProfile unit tests; use before long mutation runs |
| `tests/regression/*.py` | Tier 4A (sim soak, docgen; optional Cosmic Ray mutation) |
| `tests/static/*.py` | Per-tool static analysis runners |

Install: `pip install -e .` for runtime; `pip install -r requirements-dev.txt` for pytest, docs, static analysis, and mutation checks. See `docs/testing/README.md` and `docs/testing/regression-test-procedure.md`.

## Doc hygiene

- Public `col.*` APIs and `scripts/` maintainer entry points use Sphinx field docstrings (`:param:`, `:type:`, `:returns:`, `:rtype:`, `:raises:`), not Google-style `Args:` blocks.
- When behavior changes, update `docs/scope.md` and Sphinx guides as needed; archived planning docs are historical only.
- User-doc tracker: `docs/user-documentation.md`.
- `python -m colosseum.runner.cli` requires `if __name__ == "__main__": main()` in `runner/cli.py` (module is not executed when imported).

## Workflow

When completing changes, increment the version number using the following guidelines:
Use a semantic versioning scheme, i.e. major.minor.incremental (0.10.1, for example)
Agents cannot increment the major number. It is incremented after substantial changes that are not backwards compatible.
The minor number is to be incremented with the addition of new functionality, modules, or large changes within a module.
Incremental numbers are used for the remainder of the changes. Documentation changes do not require a version increment, unless they are significant.
