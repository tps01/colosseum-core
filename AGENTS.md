# AGENTS.md

Baseline expectations for AI agents in this repository.

## Purpose

- Normative docs: `docs/mvp/scope.md`, `docs/sphinx/source/guides/`, `examples/`, and code. Bench config keys: run `python scripts/docgen/build_all.py` (generated **Bench configuration reference**). ADRs/FFOs/DDDs are design history (see `docs/archive/README.md` for removed files).
- Small, reviewable diffs. No commits unless asked. Read `RULES.md` at task start (user-owned; do not edit unless asked).

## API and examples

- User import: `import colosseum as col`. End-of-run: **`col.endex()`** only (flush logs/DB, `summary.txt`, `summary.json`, exit `0`/`1`). Do not gate exit via `read_verifications()` loops.
- Example/test scripts: **one line per `col.*` call** with inline keyword args (see `examples/`).
- Offline/CI bench: `examples/configs/bench.sim.toml` (`driver = "sim"`) or `COLOSSEUM_BENCH_CONFIG=bench.sim.toml`. PyVISA-sim: `examples/configs/bench.visa-sim.toml` and `pytest -m visa_sim` (Python 3.10+). RF PyVISA-sim: `examples/configs/bench.rf.visa-sim.toml`.

## Repository layout

| Path | Role |
|------|------|
| `colosseum/` | Core: config, context, decorators, DB, runner (`run`, `run-suite`), plugins registry |
| `colosseum_equipment/` | Plugin → `col.equipment.*` and `col.io.*` (PSU/DMM/VSG/speca/SCPI; DIO/I2C/SPI stubs; `visa`/`serial`/`sim`) |
| `colosseum_shared/` | Plugin → `col.shared.*` (SSH, regex, parsing; `sim`/paramiko) |
| `docs/` | Planning (FFO/DDD/ADR); user guides are **not** here |
| `docs/sphinx/source/guides/` | Hand-written Sphinx RST |
| `outputs/` | Run artifacts (`debug.log`, `execution.sqlite`, `summary.txt`, `summary.json`) — gitignored |
| `build/` | Docgen staging + HTML — gitignored |

**Entry points:** `colosseum.plugins` (runtime `register(registry)`), `colosseum.docgen` (`docgen_entry:spec` → `DocgenModuleSpec`). Monorepo dev works without install via built-in fallbacks in `plugins/loader.py` and `docgen/discover.py`.

## MVP implementation status

Waves 1–3 are implemented: single-test + suite runners, plugins, optional verifications, `summary.txt`, `col.database.read_*`, vendor models `keysight-edu34450a` / `tdk-genesys` in equipment factory. RF VSG/speca (Wave A/B) with `keysight-esg`, `keysight-e4407b`, `tektronix-rsa5100b`. Post-MVP: parallel suites, JSON-schema config, context-manager API, etc. (`docs/mvp/scope.md`).

## Scripts

| Script | Use |
|--------|-----|
| `scripts/docgen/build_all.py` | Full Sphinx site → `build/docgen/site/html/` |
| `scripts/docgen/build_module.py` | Autodoc RST for one package |
| `scripts/cleanup.py` | Remove `outputs/`, `build/`, `__pycache__`, etc. — **`--dry-run` first** |
| `scripts/run_tests.py` | `pytest` tiers 1–3; `--regression` for soak + docgen |
| `scripts/profile_unit_tests.py` | cProfile unit tests; use before long mutation runs |
| `tests/regression/*.py` | Tier 4A (sim soak, docgen; optional Cosmic Ray mutation) |

Install: `pip install -e .` for runtime; `pip install -r requirements-dev.txt` for pytest, docs, and mutation checks. See `docs/testing/README.md` and `docs/testing/regression-test-procedure.md`.

## Doc and design hygiene

- Update FFO/DDD cross-refs when behavior changes. User-doc tracker: `docs/mvp/user-documentation.md`.
- `python -m colosseum.runner.cli` requires `if __name__ == "__main__": main()` in `runner/cli.py` (module is not executed when imported).
