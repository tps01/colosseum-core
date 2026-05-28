# Colosseum

Colosseum is a Python test automation framework for embedded and bench-style system testing. Test scripts import `colosseum as col`, call high-level measurement and verification APIs, and finish with `col.endex()` so logs, SQLite evidence, `summary.txt`, resource cleanup, and process exit status are handled consistently.

The current implementation includes the core runtime, CLI runner, suite runner, plugin registry, simulated bench support, equipment/shared plugins, reference DMM/PSU models, SQLite read helpers, Sphinx doc generation, regression scripts, and optional Cosmic Ray mutation testing.

## Install From This Checkout

Windows PowerShell:

```powershell
.\scripts\start_environment.ps1
```

Windows `cmd.exe`, including systems where PowerShell script execution is disabled:

```bat
scripts\start_environment.bat
```

Linux/macOS shell:

```sh
. ./scripts/start_environment.sh
```

These scripts create `.venv`, install the project in editable mode with test and mutation extras, and activate the environment. The POSIX shell version should be sourced with `.` if you want activation to remain in the current shell.

Override defaults as needed:

```powershell
$env:EXTRAS = "bench,test,docs,mutation"
.\scripts\start_environment.ps1
```

```bat
set EXTRAS=bench,test,docs,mutation
scripts\start_environment.bat
```

```sh
EXTRAS=bench,test,docs,mutation . ./scripts/start_environment.sh
```

Manual install:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[bench,test,docs,mutation]"
```

Core-only installs need only:

```powershell
python -m pip install -e .
```

## Quickstart

Run the simulated power-rail example without bench hardware:

```powershell
colosseum run examples/test_power_rails.py --config examples/configs/bench.sim.toml
```

Run a suite:

```powershell
colosseum run-suite tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml
```

Direct Python scripts are also supported. In direct mode, the script owns finalization:

```python
import colosseum as col

def main() -> None:
    col.config.load_config("examples/configs/bench.sim.toml")
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
    col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)

if __name__ == "__main__":
    main()
    col.endex()
```

Each run writes `outputs/<timestamp>_<name>/debug.log`, `execution.sqlite`, and `summary.txt`.

## Implemented Capabilities

- Runtime context initialized by `col.config.load_config(...)`, `colosseum run`, or `colosseum run-suite`.
- TOML bench configuration with normalized single-table and array-of-table sections.
- `@measurement` and `@verification` decorators with required and optional verification aggregation.
- `col.endex()` as the only supported end-of-run API.
- CLI commands: `colosseum run` and `colosseum run-suite`.
- Suite TOML with `name`, `setup`, `tests`, and `teardown` lists.
- Local evidence: `debug.log`, `execution.sqlite`, `summary.txt`.
- Public database read helpers: `col.database.read_measurements()`, `read_verifications()`, `read_run_metadata()`, and guarded `read_table(...)`.
- Plugin entry points for runtime namespaces and doc generation.
- First-party `col.equipment.*` and `col.shared.*` namespaces.
- Simulated, VISA, serial, and SSH-backed bench paths depending on installed extras.
- Generic DMM/PSU SCPI support plus `keysight-edu34450a` and `tdk-genesys` model selection.
- Sphinx/docgen scripts under `scripts/docgen/`.
- Test tiers and optional Cosmic Ray mutation driver under `scripts/` and `tests/regression/`.

## Development

Run unit tests:

```powershell
python -m pytest tests/unit
```

Run all default pytest tiers:

```powershell
python scripts/run_tests.py
```

Profile unit tests:

```powershell
python scripts/profile_unit_tests.py
```

Run one mutation target:

```powershell
python tests/regression/run_mutation.py --run --target colosseum/results/aggregation.py
```

Clean generated artifacts:

```powershell
python scripts/cleanup.py --dry-run
python scripts/cleanup.py
```

## Documentation

- [Implemented MVP status](docs/mvp/scope.md)
- [Project documentation map](docs/README.md)
- [User guides](docs/sphinx/source/guides/)
- [Testing guide](docs/testing/README.md)
- [Original architecture sketch](scratchpad/colosseum_architecture_document.md)

The FFO, DDD, and ADR documents remain useful design history. The current implementation status and known gaps are summarized in `docs/mvp/scope.md`.
