# Colosseum Examples

These scripts exercise the implemented user-facing API. For offline runs without bench hardware, use [configs/bench.sim.toml](configs/bench.sim.toml), which uses `driver = "sim"`.

**Style:** Colosseum API calls in examples use a single line per invocation with keyword arguments inline.

## Scripts

| Script | What it exercises |
|--------|-------------------|
| [test_power_rails.py](test_power_rails.py) | Config load, PSU/DMM measurement and verification, optional verification, raw SCPI helper |
| [test_ssh_health.py](test_ssh_health.py) | SSH stdout measurement, regex verification, `col.endex()` aggregation/exit |

## Config

- [configs/bench.sim.toml](configs/bench.sim.toml): simulated PSU, DMM, serial, and SSH resources for local development and CI.
- [configs/bench.toml](configs/bench.toml): real bench-style entries for VISA/serial/SSH usage. Adjust resources, credentials, and models for your lab.

## Commands

```powershell
# Simulated bench, no hardware
colosseum run examples/test_power_rails.py --config examples/configs/bench.sim.toml

# Simulated SSH/regex flow
colosseum run examples/test_ssh_health.py --config examples/configs/bench.sim.toml

# Real bench, after editing examples/configs/bench.toml for your resources
colosseum run examples/test_power_rails.py --config examples/configs/bench.toml
```

Suite orchestration is implemented through `colosseum run-suite`. The repository includes suite fixtures under `tests/fixtures/suites/`; production projects should keep suite TOML beside their own tests.

## Related Documentation

- [Top-level README](../README.md)
- [Implemented MVP status](../docs/mvp/scope.md)
- [User guides](../docs/sphinx/source/guides/)
- [Testing guide](../docs/testing/README.md)
