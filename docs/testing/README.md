# Colosseum testing

## Prerequisites

```bash
pip install -e ".[test,mutation]"
```

For docgen regression: `pip install -e ".[docs]"`. For hardware procedure: `.[bench]`.
The standard `scripts/start_environment.ps1` setup installs both `test` and `mutation`.

## Tiers 1–3 (pytest, sim bench)

From the repository root:

```bash
python scripts/run_tests.py
# or
pytest tests/unit tests/integration tests/e2e -q
```

| Tier | Path | What it covers |
|------|------|----------------|
| Unit | `tests/unit/` | Normalization, aggregation, decorators, DB, suite parse, sim contracts |
| Integration | `tests/integration/` | `load_config`, `endex`, `run_suite`, plugins, equipment/shared sim |
| E2E | `tests/e2e/` | Subprocess `colosseum run` / `run-suite`; `examples/` + `tests/fixtures/` |

Tests use pytest `tmp_path` for `outputs/` (not the repo tree).

## Profiling unit tests

Mutation testing and repeated pytest runs are only as fast as the unit suite. Profile hot paths with:

```bash
python scripts/profile_unit_tests.py
python scripts/profile_unit_tests.py --sort tottime --limit 50
python scripts/profile_unit_tests.py --stats build/profile/unit_tests.prof
```

The script runs `tests/unit` under `cProfile`, prints project-scoped `pstats` tables (cumulative and self time), and includes pytest’s slowest-test report (`--durations=15`). Optional `.prof` output works with [snakeviz](https://jiffyclub.github.io/snakeviz/) if installed.

## Tier 4A — Scripted regression (no hardware)

| Script | Requirement | Notes |
|--------|-------------|--------|
| `tests/regression/run_soak_sim.py` | R-SOAK-01 | Default 50× `run-suite` on sim; `--count N` |
| `tests/regression/run_docgen_check.py` | R-DOC-01 | Runs `scripts/docgen/build_all.py` |
| `tests/regression/run_mutation.py` | R-MUT-01 | Optional; `--run` needs `.[mutation]`; reports go under `build/mutation/` |

```bash
python scripts/run_tests.py --regression
```

## Tier 4B — Hardware / QEMU procedure

When a bench or QEMU guest exists, follow [regression-test-procedure.md](regression-test-procedure.md) and complete [templates/regression-signoff.md](templates/regression-signoff.md).

## Environment

- Sim config: `examples/configs/bench.sim.toml`
- `COLOSSEUM_BENCH_CONFIG=bench.sim.toml` for examples that read env
- Local secrets: `configs/bench.local.toml` (gitignored pattern `**/bench.local.toml`)
