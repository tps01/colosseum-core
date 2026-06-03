# Colosseum Implemented MVP Status

## Purpose

This document is the current implementation summary for the Colosseum MVP. It replaces the earlier wave-planning view with what is actually present in the repository as of version `0.3.0`.

The original feature overviews, detailed design documents, and ADRs remain useful design history; some pre-MVP files were removed from the tree (see [docs/archive/README.md](../archive/README.md) and git tag `doc-snapshot-pre-archive`). When documents still use "Wave 1/2/3" language, read that as historical sequencing unless this document says otherwise.

## Product Summary

Colosseum is a Python-importable, offline-first, plugin-oriented test automation framework for embedded system integration and acceptance testing on a bench. Users write ordinary Python scripts with `import colosseum as col`, load TOML bench configuration, perform measurements and verifications, and produce local execution evidence.

The supported end-of-run API is `col.endex()`. It writes final metadata, writes `summary.txt` and `summary.json`, flushes/closes logging and SQLite, runs plugin shutdown hooks, closes cached resources, and exits with code `0` or `1`.

## Compatibility

| Area | Implemented status |
|------|--------------------|
| Python | `>=3.9` (`pyvisa` 1.14.x on 3.9, `>=1.15` on 3.10+) |
| Platforms | Windows and Linux-oriented code paths; current local validation has been on Windows |
| Network | No cloud dependency; hardware/SSH uses bundled runtime dependencies |
| User import | `import colosseum as col` |
| Packaging | One source project containing `colosseum`, `colosseum_equipment`, and `colosseum_shared` packages |
| Default install | Full runtime (VISA, serial, SSH, GUI); dev tools via git clone + `requirements-dev.txt` |
| Offline tarballs | End-user runtime wheels only (from `scripts/package_offline.py`); no pytest/Sphinx/docgen/PyVISA-sim |
| Optional extras | `test` (pytest + PyVISA-sim on 3.10+), `docs`, `mutation` (dev); deprecated aliases `bench`, `gui`, `equipment-sim` → visa-sim, etc. |
| Documentation generation | Sphinx/docgen scripts under `scripts/docgen/` |

## Implemented Runtime Behavior

### Core Runtime

- Global runtime context with config, database, logger, plugin registry, resource cache, phase, and result aggregator.
- Context initialization through `col.config.load_config(...)`, `colosseum run`, or `colosseum run-suite`.
- Lazy output directory creation under `outputs/<timestamp>_<logical-name>/`.
- `debug.log`, `execution.sqlite`, `summary.txt`, and `summary.json` are produced for finalized runs.
- `col.endex()` is idempotent enough to preserve the first final exit code if called again.

### Configuration

- TOML loading uses `tomllib` on Python 3.11+ and `tomli` on older Python.
- Plugin-registered config sections are normalized from either a single table or an array of tables.
- Implemented first-party sections include `equipment.psu`, `equipment.dmm`, `equipment.serial`, `equipment.vsg`, `equipment.speca`, and `shared.ssh`. Lab entries omit `driver` to use default VISA/SCPI.
- Required keys are enforced when resources are required.
- Unknown keys are collected as warnings on the runtime context.

### Measurements And Verifications

- `@measurement` records command/domain/key evidence in SQLite.
- Single-row measurements reject duplicate keys for the same domain and command.
- `multi_row=True` measurements require `row_index`.
- `@verification` records PASS, FAIL, or ERROR.
- Verification sources are explicit through `MeasurementSource`.
- Required FAIL/ERROR fails the run; optional FAIL/ERROR is recorded but does not fail the aggregate result.
- Plugin module prefixes map verification and measurement domains to `equipment` or `shared`.

### CLI And Suites

- `colosseum run <test.py> --config <bench.toml>` initializes runtime, loads config, executes the script with `runpy`, calls `main()`, and finalizes with `col.endex()`.
- The CLI does not execute a script's `if __name__ == "__main__"` block.
- `colosseum run-suite <suite.toml> --config <bench.toml>` runs setup scripts, test scripts, and teardown scripts in one runtime context and one output directory.
- Suite paths are relative to the suite file.
- Setup failure marks the suite failed, skips tests, still runs teardown, and exits `1`.
- Teardown failure marks the run failed and exits `1`.
- Test script failures are logged, marked as suite errors, and the suite continues to teardown and remaining tests before exiting `1`.

### Evidence And Read APIs

- SQLite tables store measurements, verifications, events, artifacts, and run metadata.
- Public read helpers are implemented:
  - `col.database.read_measurements()`
  - `col.database.read_verifications()`
  - `col.database.read_run_metadata()`
  - `col.database.read_table(...)` for allowed core tables and `plugin_*` tables
- Offline read helpers are implemented through `colosseum.database.read_from_path.read_from_path(sqlite_path)` for completed run databases.
- Read helpers are for inspection and tooling. Test scripts should not compute final exit status from read helpers; use `col.endex()`.

### Plugins

- Runtime plugins use the `colosseum.plugins` entry point and a `register(registry)` function.
- Plugins may register namespaces, config sections, validators, and shutdown hooks.
- Documentation plugins use the `colosseum.docgen` entry point and return `DocgenModuleSpec`.
- First-party `col.equipment.*` and `col.shared.*` are registered through the same plugin path used by third-party extensions.

### Equipment And Shared Utilities

- `col.equipment.psu` supports voltage/current/output operations and PSU voltage measurement.
- `col.equipment.dmm` supports voltage measurement and voltage verification.
- `col.equipment.scpi` exposes raw SCPI write/query/query-float helpers.
- Simulated transports are available for offline development and CI.
- VISA and serial transports are available when the `equipment` or `bench` extras are installed.
- Generic SCPI DMM/PSU drivers are implemented.
- `col.equipment.vsg` and `col.equipment.speca` support CW VSG control, swept spectrum markers/traces, and vendor models `keysight-esg`, `keysight-e4407b`, and `tektronix-rsa5100b`.
- Reference model selection includes `keysight-edu34450a` and `tdk-genesys`.
- `col.shared.ssh.measure_stdout` records command output.
- `col.shared.regex.verify_match` verifies a regex against a measured source.
- SSH uses a simulated client for `driver = "sim"` and Paramiko (included in the default install).

### Testing And Regression

- `scripts/run_tests.py` runs the standard pytest tiers.
- `scripts/profile_unit_tests.py` profiles unit tests and prints project-scoped `pstats` output.
- `tests/regression/run_docgen_check.py` checks doc generation.
- `tests/regression/run_soak_sim.py` runs simulated soak coverage.
- `tests/regression/run_mutation.py` runs optional Cosmic Ray mutation tests and writes reports under `build/mutation/`.
- The mutation runner serializes itself with a lock because Cosmic Ray mutates the working tree while testing.

## Current User Documentation

Hand-written Sphinx guides exist under `docs/sphinx/source/guides/` for:

- Installation
- Quickstart
- Configuration
- Running tests
- Running suites
- Output artifacts
- Exit codes
- Measurements and verifications
- Plugin development
- Platform notes

Autodoc staging and site build scripts live under `scripts/docgen/`.

## Known Differences From The Original Plan

These are the meaningful differences or losses from the planning documents that may be worth addressing later.

| Area | Original plan | Implemented now | Follow-up consideration |
|------|---------------|-----------------|-------------------------|
| Package distribution | Separate `colosseum`, `colosseum-equipment`, and `colosseum-shared` distributions | One source project/package build with three import packages and optional extras | Split distributions before publishing if independent release/install boundaries matter |
| Plugin collision policy | Later fail-fast or user-selected collision handling was considered | Duplicate namespaces/config specs log warnings and replace prior registrations | Decide whether collisions should be hard errors |
| Config validation | Richer schema validation was deferred | Registered section specs, required/optional keys, and validators exist; no JSON schema | Add schema export/validation if config UX needs stronger guarantees |
| Environment substitution | `${ENV}` style config substitution was mentioned as post-MVP | Not implemented | Add only if bench configs need portable secret/resource injection |
| Suite test exceptions | Plans emphasized setup/teardown state and aggregate exit semantics | Setup, teardown, and test script exceptions fail the run; suite execution still continues to teardown where possible | Consider adding a configurable fail-fast/continue policy if suite throughput needs differ |
| Public SQLite schema | Stable public schema guarantee was deferred | SQLite schema and read helpers are usable, but schema stability is not promised | Add schema versioning before external tools depend on raw tables |
| Offline database reads | Possible `read_from_path(sqlite_path)` was deferred | Read-only offline reader is implemented for measurements, verifications, metadata, and allowed tables | Keep the offline reader aligned with active read-helper allowlists |
| Reporting formats | HTML/JUnit/Allure were deferred | `summary.txt`, `summary.json`, `debug.log`, and SQLite are implemented | Add richer CI/reporting formats if needed |
| Parallel execution | Parallel suites and multiprocessing were deferred | Suite execution is serial; mutation tests are explicitly serialized | Keep serial unless bench resource isolation is designed |
| Context manager API | `with col.run(...)` was a future idea | Not implemented; use CLI or explicit `load_config` plus `col.endex()` | Revisit if direct Python ergonomics need it |
| Equipment breadth | Future architecture mentioned more lab protocols | Core DMM/PSU/VSG/speca plus stub kinds: ``attn``, ``pwrmeter``, ``rfswitch``, ``oscope``, ``eload``, ``freqcounter``, ``vna``, ``sdr``; ``col.io`` (DIO/I2C/SPI) stubs for NI drivers | Vendor ``model`` drivers and NI/UHD SDK bindings need host manuals |
| Documentation polish | Full user docs and generated API reference were planned | Guide drafts and docgen pipeline exist; public docs are not published from CI | Add CI doc build/publish if this becomes a released package |

## Explicitly Deferred

- Parallel suite execution.
- Context-manager runtime API.
- JSON-schema config validation.
- Stable public SQLite schema guarantee.
- Rich CLI filtering/retries.
- HTML/JUnit/Allure reports.
- Test generation, model-based testing, and ALM export.
- Broader equipment families such as CAN, JTAG, DAQ, and socket transport (stub APIs exist for RF path, oscope, e-load, VNA phase-1, SDR; NI 845x/6501 via ``col.io`` pending documentation).
