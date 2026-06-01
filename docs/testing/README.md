# Colosseum testing

## Prerequisites

```bash
pip install -e .
pip install -r requirements-dev.txt
```

For docgen regression only: ensure `requirements-dev.txt` is installed (includes Sphinx).
For hardware procedure: runtime is included in `pip install -e .`; add `requirements-dev.txt` for pytest helpers.
The standard `scripts/start_environment.ps1` setup installs runtime plus dev requirements.

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

## PyVISA-sim (Python 3.10+)

Semi-realistic SCPI mocks from YAML (PyVISA-sim is included in the default install):

```bash
pytest -m visa_sim -q
```

See [pyvisa-sim-fixtures.md](pyvisa-sim-fixtures.md).

## Suite test script exceptions

Documented behavior when a test script raises: [suite-test-script-errors.md](suite-test-script-errors.md).

## Tier 4B — Hardware procedure

When a bench exists, copy [../configs/bench.local.toml.example](../configs/bench.local.toml.example) to ``configs/bench.local.toml``, follow [regression-test-procedure.md](regression-test-procedure.md), and complete [templates/regression-signoff.md](templates/regression-signoff.md).

## Tier 4C — QEMU / Yocto lab (manual)

Poky ``qemux86-64`` image for offline install, SSH DUT endpoint, and X11 GUI regression. **Not** in GitHub Actions CI.

See [qemu-yocto-regression.md](qemu-yocto-regression.md) and [infra/yocto/README.md](../../infra/yocto/README.md).

```bash
./infra/yocto/scripts/qemu-up.sh
./infra/yocto/run_all_regression.sh --skip-gui-interactive
```

## Environment

- Sim config: `examples/configs/bench.sim.toml`
- `COLOSSEUM_BENCH_CONFIG=bench.sim.toml` for examples that read env
- Local secrets: `configs/bench.local.toml` (gitignored pattern `**/bench.local.toml`)
