# Colosseum examples (implementation targets)

These scripts describe the user-facing API. For offline runs without bench hardware, use [configs/bench.sim.toml](configs/bench.sim.toml) (`driver = "sim"`).

**Style:** Colosseum API calls in examples use a single line per invocation (all keyword arguments on one line), matching the architecture doc sketch.

## Scripts

| Script | Target wave | What it exercises |
|--------|-------------|-------------------|
| [test_power_rails.py](test_power_rails.py) | Wave 2 | `load_config`, PSU/DMM measure+verify, optional verify, SCPI shorthand |
| [test_ssh_health.py](test_ssh_health.py) | Wave 2 | SSH measure, regex verify, `endex()` for aggregation/exit |

## Config

[configs/bench.toml](configs/bench.toml) — example `equipment.*` and `shared.ssh` sections aligned with [docs/features/ffo-bench-configuration.md](../docs/features/ffo-bench-configuration.md).

## Commands

```bash
# Simulated bench (no hardware)
set COLOSSEUM_BENCH_CONFIG=bench.sim.toml   # Windows
export COLOSSEUM_BENCH_CONFIG=bench.sim.toml   # Linux
colosseum run examples/test_power_rails.py --config examples/configs/bench.sim.toml

# Real bench (VISA / SSH) — use examples/configs/bench.toml with drivers visa/ssh
colosseum run examples/test_power_rails.py --config examples/configs/bench.toml
```

Automated validation: `python scripts/run_tests.py` (from repo root).

Suite orchestration (Wave 3) would reference these from a `suites/*.toml` file; see [docs/features/ffo-test-suites.md](../docs/features/ffo-test-suites.md).

## Related documentation

- [docs/mvp/scope.md](../docs/mvp/scope.md) — wave boundaries and success scenarios
- [scratchpad/colosseum_architecture_document.md](../scratchpad/colosseum_architecture_document.md) — original API sketch
