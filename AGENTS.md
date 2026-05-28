# AGENTS.md

Baseline expectations for AI agents in this repository.

## Purpose

- Align with `docs/`, `scratchpad/`, and `examples/`; treat ADRs/DDDs as source-of-truth unless the user overrides.
- Small, reviewable diffs. No commits unless asked. Read `RULES.md` at task start (user-owned; do not edit unless asked).

## API and examples

- User import: `import colosseum as col`. End-of-run: **`col.endex()`** only (flush logs/DB, `summary.txt`, exit `0`/`1`). Do not gate exit via `read_verifications()` loops.
- Example/test scripts: **one line per `col.*` call** with inline keyword args (see `examples/`).
- Offline/CI bench: `examples/configs/bench.sim.toml` (`driver = "sim"`) or `COLOSSEUM_BENCH_CONFIG=bench.sim.toml`.

## Repository layout

| Path | Role |
|------|------|
| `colosseum/` | Core: config, context, decorators, DB, runner (`run`, `run-suite`), plugins registry |
| `colosseum_equipment/` | Plugin → `col.equipment.*` (PSU/DMM/SCPI; `visa`/`serial`/`sim`) |
| `colosseum_shared/` | Plugin → `col.shared.*` (SSH, regex, parsing; `sim`/paramiko) |
| `docs/` | Planning (FFO/DDD/ADR); user guides are **not** here |
| `docs/sphinx/source/guides/` | Hand-written Sphinx RST |
| `outputs/` | Run artifacts (`debug.log`, `execution.sqlite`, `summary.txt`) — gitignored |
| `build/` | Docgen staging + HTML — gitignored |

**Entry points:** `colosseum.plugins` (runtime `register(registry)`), `colosseum.docgen` (`docgen_entry:spec` → `DocgenModuleSpec`). Monorepo dev works without install via built-in fallbacks in `plugins/loader.py` and `docgen/discover.py`.

## MVP implementation status

Waves 1–3 are implemented: single-test + suite runners, plugins, optional verifications, `summary.txt`, `col.database.read_*`, vendor models `keysight-edu34450a` / `tdk-genesys` in equipment factory. Post-MVP: parallel suites, JSON-schema config, context-manager API, etc. (`docs/mvp/scope.md`).

## Scripts

| Script | Use |
|--------|-----|
| `scripts/docgen/build_all.py` | Full Sphinx site → `build/docgen/site/html/` |
| `scripts/docgen/build_module.py` | Autodoc RST for one package |
| `scripts/cleanup.py` | Remove `outputs/`, `build/`, `__pycache__`, etc. — **`--dry-run` first** |
| `scripts/run_tests.py` | `pytest` tiers 1–3; `--regression` for soak + docgen |
| `scripts/profile_unit_tests.py` | cProfile unit tests; use before long mutation runs |
| `tests/regression/*.py` | Tier 4A (sim soak, docgen; optional Cosmic Ray mutation) |

Install: `pip install -e ".[test,mutation]"` for pytest and mutation checks; `.[bench,docs]` as needed. See `docs/testing/README.md` and `docs/testing/regression-test-procedure.md`.

## Doc and design hygiene

- Update FFO/DDD cross-refs when behavior changes. User-doc tracker: `docs/mvp/user-documentation.md`.
- `python -m colosseum.runner.cli` requires `if __name__ == "__main__": main()` in `runner/cli.py` (module is not executed when imported).
