# Analysis and profiling layers

Colosseum separates **quality checks** into four layers. Use the right tool for the question; do not conflate wall-clock CI timing with in-process CPU profiling.

## Layer map

| Layer | Question | Entry point | CI |
|-------|----------|-------------|-----|
| **Static** | Lint, types, security, dead code? | [`scripts/run_static.py`](../../scripts/run_static.py) → [`tests/static/`](../../tests/static/) | Blocking PR |
| **Speed (in-process)** | Where is CPU time in pytest or a CLI run? | [`scripts/profile_tests.py`](../../scripts/profile_tests.py), [`scripts/profile_run.py`](../../scripts/profile_run.py) | None |
| **Wall-clock** | Which CI jobs/steps are slow? | [`scripts/ci/profile_local.py`](../../scripts/ci/profile_local.py), [`ci-timing.md`](ci-timing.md) | Instrumented summaries |
| **Dynamic** | Do tests catch bugs? Does the stack endure? | [`tests/regression/`](../../tests/regression/) (mutation, soak, offline, docgen) | Selective / advisory |

Bench runtime evidence (`execution.sqlite`, `debug.log`, `summary.json`) answers **what happened on a run**, not **where code spent CPU time**.

## Vocabulary

| Term | Meaning | Agent default? |
|------|---------|----------------|
| Static analysis | No code execution; ruff, mypy, bandit, vulture | Yes |
| Speed profiling | cProfile during pytest or `colosseum run` | Optional local |
| Wall-clock profiling | Job/step timing (`TIMING …=Xs`) | Optional / maintainer |
| Dynamic analysis | Code run with altered inputs or repeated loads | Selective |
| ↳ Mutation | Cosmic Ray mutants vs unit tests | Single-target + `--verify-only` |
| ↳ Soak / endurance | Repeated sim suite runs | `--regression` / CI ×5 |
| ↳ Memory snapshot | `tracemalloc` peak on one script (`profile_run --tracemalloc`) | Targeted debug only |
| Coverage | Line hit counts | **Advisory only** — see [`RULES.md`](../../RULES.md) |

## Speed profiling (pytest tiers)

```bash
python scripts/profile_tests.py --tier unit
python scripts/profile_tests.py --tier integration
python scripts/profile_tests.py --tier e2e
python scripts/profile_tests.py --tier all
python scripts/profile_tests.py --tier unit --sort tottime --stats build/profile/unit.prof
```

[`scripts/profile_unit_tests.py`](../../scripts/profile_unit_tests.py) remains a backward-compatible alias for `--tier unit`.

**E2E limitation:** E2E tests often spawn `colosseum` subprocesses. cProfile on the pytest process does **not** profile child-process CPU. For runtime CLI paths, use [Runtime profiling](#runtime-profiling-colosseum-not-pytest) below.

## Runtime profiling (Colosseum, not pytest)

Separate **test harness CPU** (pytest) from **runtime CPU** (config load, script execution, SQLite, summary). [`profile_tests.py`](../../scripts/profile_tests.py) profiles pytest and test code in-process; this section profiles the Colosseum runtime only.

| Entry | Typical use | Tool |
|-------|-------------|------|
| `colosseum run` | Single test script | [`profile_run.py`](../../scripts/profile_run.py) |
| `colosseum run-suite` | Suites, multi-script runs | [`profile_run.py --suite`](../../scripts/profile_run.py) |
| Direct Python (`import colosseum as col`) | Examples, notebooks | Manual cProfile or `profile_run --tracemalloc` |
| Soak / endurance | Repeated suite stability | [`profile_local --job soak`](../../scripts/ci/profile_local.py) (wall-clock) |

Sim bench configs (unless profiling hardware-specific paths):

- [`scripts/offline_smoke/bench.sim.toml`](../../scripts/offline_smoke/bench.sim.toml) — minimal smoke
- [`examples/configs/bench.sim.toml`](../../examples/configs/bench.sim.toml) — richer examples
- `COLOSSEUM_BENCH_CONFIG=bench.sim.toml` for examples that read env

**Durability note:** Pytest sets `COLOSSEUM_DEFER_DB_COMMITS=1` to batch SQLite commits. [`profile_run.py`](../../scripts/profile_run.py) and manual CLI profiling start a fresh process without that variable (production-like per-insert commits).

### Single script — `colosseum run`

```bash
# CPU (cProfile) — default build/profile/run.prof
python scripts/profile_run.py scripts/offline_smoke/run_sim.py --config scripts/offline_smoke/bench.sim.toml
python scripts/profile_run.py --sort tottime --limit 25 examples/test_power_rails.py --config examples/configs/bench.sim.toml
python scripts/profile_run.py --stats build/profile/power_rails.prof examples/test_power_rails.py --config examples/configs/bench.sim.toml

# Memory peak (in-process, stdlib)
python scripts/profile_run.py --tracemalloc scripts/offline_smoke/run_sim.py --config scripts/offline_smoke/bench.sim.toml

# Interactive flame graph (optional: pip install snakeviz)
python -m snakeviz build/profile/run.prof
```

Manual equivalent:

```bash
python -m cProfile -o build/profile/run.prof -m colosseum.runner.cli run \
  examples/test_power_rails.py --config examples/configs/bench.sim.toml
python -m pstats build/profile/run.prof
```

Short smokes mostly show **import and plugin load** ([`colosseum/runner/cli.py`](../../colosseum/runner/cli.py), [`plugins/loader.py`](../../colosseum/plugins/loader.py)). Use a representative example (`examples/test_power_rails.py`, `examples/test_rf_bench_integration.py`) to see decorator, DB, and config hot paths.

### Suite — `colosseum run-suite`

```bash
python scripts/profile_run.py --suite tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml
python scripts/profile_run.py --suite tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml -d
python scripts/profile_run.py --suite --stats build/profile/suite.prof \
  tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml
```

Manual equivalent:

```bash
python -m cProfile -o build/profile/suite.prof -m colosseum.runner.cli run-suite \
  tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml
```

**Endurance (wall-clock, not CPU path detail):**

```bash
python scripts/ci/profile_local.py --job soak
python tests/regression/run_soak_sim.py --count 10
```

### Direct Python — `import colosseum as col`

**A. Through CLI** (includes runner, `run_script`, and `main()`): same as single-script commands above.

**B. In-process cProfile** (no CLI argparse overhead):

```bash
python -m cProfile -o build/profile/direct.prof -c "
from pathlib import Path
from colosseum.config import load_config
from colosseum.context import init_context
from colosseum.runner.single_test import run_script
from colosseum.results import endex
import colosseum as col  # noqa: F401

bench = Path('examples/configs/bench.sim.toml')
init_context(test_case_name='profile_direct', config_path=bench)
load_config(bench)
run_script(Path('examples/test_power_rails.py'))
endex()
"
```

Or keep a one-off driver under `scratchpad/` (gitignored).

### Interpreting `.prof` output

- **High cumulative time on `<module>` / imports:** cold start; rerun or use a heavier script.
- **High `tottime` on `database/manager` or `decorators/`:** runtime hot path during the script.
- **Filter pstats** on `colosseum`, `colosseum_equipment`, `colosseum_shared`, `colosseum_host` (as `profile_run.py` does).

### What runtime profiling does not cover

| Scenario | Tool | Why |
|----------|------|-----|
| Hardware / VISA / autoconfig | Manual run + `configs/bench.local.toml` | Needs instruments; sim hides transport |
| GUI (`colosseum --gui`) | Manual / OS tools | Separate entry point |
| Post-run evidence | `execution.sqlite`, `debug.log` | What happened, not CPU time |
| CI job duration | [`profile_local.py`](../../scripts/ci/profile_local.py), [ci-timing.md](ci-timing.md) | Wall-clock, not cProfile |

## Wall-clock CI mirrors

```bash
python scripts/ci/profile_local.py --job test
python scripts/ci/profile_local.py --job docgen-html
python scripts/ci/profile_local.py --job soak
python scripts/ci/profile_local.py --job mutation   # slow; requires .[mutation]
```

Historical GitHub Actions summaries: [`scripts/ci/summarize_runs.py`](../../scripts/ci/summarize_runs.py) (requires `gh auth login`).

## Agent playbook

```bash
# Correctness (default)
python scripts/run_tests.py
python scripts/run_static.py

# Speed: pytest hot paths (includes test harness)
python scripts/profile_tests.py --tier unit --sort tottime

# Speed: Colosseum runtime (not pytest) — see Runtime profiling in analysis.md
python scripts/profile_run.py examples/test_power_rails.py --config examples/configs/bench.sim.toml
python scripts/profile_run.py --suite tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml

# Dynamic test quality (slow)
python tests/regression/run_mutation.py --run --target colosseum/results/aggregation.py

# Wall-clock parity with CI
python scripts/ci/profile_local.py --job docgen-html
```

## Deferred (out of scope)

| Technique | Why deferred |
|-----------|--------------|
| pytest-cov / coverage gates | Conflicts with project testing philosophy; advisory only if ever added |
| memray / scalene | Optional extra; use tracemalloc first |
| Hypothesis / fuzzing | New test style across sim boundaries |
| Valgrind / sanitizers | C-extension heavy deps; bench-host specific |
| Hardware / QEMU profiling | Tier 4B/4C manual |
| Blocking CI for cProfile or mutation | Too slow / noisy for PRs |

## Artifact locations

| Path | Contents |
|------|----------|
| `build/profile/` | cProfile `.prof` files (gitignored via `build/`) |
| `build/mutation/` | Cosmic Ray reports |
| `build/ci-timing/` | Optional CSV/markdown from `summarize_runs.py` |
