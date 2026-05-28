# Colosseum Documentation

This directory contains the current project documentation plus the design records that guided the MVP implementation.

For the current product surface, start with:

1. [Top-level README](../README.md)
2. [Implemented MVP status and known gaps](mvp/scope.md)
3. [Sphinx user guides](sphinx/source/guides/)
4. [Testing and regression](testing/README.md)
5. [Examples](../examples/)

The ADR, FFO, and DDD documents remain design history and rationale. They are useful when changing behavior, but some wave-planning language in those documents predates the implemented MVP. When there is a conflict, prefer [mvp/scope.md](mvp/scope.md), the user guides, tests, and the current code.

## Current Implementation

Colosseum 0.3.0 implements the original Waves 1-3 MVP in a single source tree:

- Core runtime, configuration load, context, decorators, result aggregation, `col.endex()`.
- CLI commands: `colosseum run` and `colosseum run-suite`.
- Suite TOML with setup, test, and teardown phases.
- Local evidence: `debug.log`, `execution.sqlite`, and `summary.txt`.
- Public database read helpers under `col.database`.
- Runtime plugin registry and docgen entry points.
- First-party `col.equipment.*` and `col.shared.*` namespaces.
- Simulated bench mode for offline development and CI.
- VISA, serial, and SSH paths through optional extras.
- Generic DMM/PSU SCPI plus `keysight-edu34450a` and `tdk-genesys` model implementations.
- Sphinx/docgen pipeline and regression scripts, including optional Cosmic Ray mutation testing.

Known differences from the original plan are captured in [mvp/scope.md](mvp/scope.md#known-differences-from-the-original-plan).

## Document Map

### Status and User Docs

| Document | Description |
|----------|-------------|
| [../README.md](../README.md) | Project overview, install, quickstart, development commands |
| [mvp/scope.md](mvp/scope.md) | Implemented MVP status, current behavior, known gaps |
| [mvp/user-documentation.md](mvp/user-documentation.md) | User documentation inventory |
| [sphinx/README.md](sphinx/README.md) | Sphinx/docgen build notes |
| [testing/README.md](testing/README.md) | Test tiers, profiling, mutation testing |

### Decisions

| ADR | Topic |
|-----|--------|
| [adr-001](decisions/adr-001-distributions.md) | Distributions and namespace |
| [adr-002](decisions/adr-002-plugin-registration.md) | Plugin registration |
| [adr-003](decisions/adr-003-config-validation.md) | Config validation |
| [adr-004](decisions/adr-004-setup-teardown-state.md) | Setup/teardown state |
| [adr-005](decisions/adr-005-database-read-api.md) | DB read API shape |
| [adr-006](decisions/adr-006-vendor-instruments.md) | Vendor DMM/PSU |
| [adr-007](decisions/adr-007-summary-artifact.md) | `summary.txt` |
| [adr-008](decisions/adr-008-output-naming.md) | Output directory naming |
| [adr-009](decisions/adr-009-plugin-namespace-collisions.md) | Namespace collisions |
| [adr-010](decisions/adr-010-endex.md) | `endex()` end-of-run API |

### Feature Overviews

| FFO | Topic |
|-----|--------|
| [ffo-single-test-execution](features/ffo-single-test-execution.md) | Single test run |
| [ffo-bench-configuration](features/ffo-bench-configuration.md) | TOML bench config |
| [ffo-measurements-verifications](features/ffo-measurements-verifications.md) | Measure / verify |
| [ffo-execution-evidence](features/ffo-execution-evidence.md) | Logs, DB, summary |
| [ffo-laboratory-equipment](features/ffo-laboratory-equipment.md) | Equipment APIs |
| [ffo-host-dut-utilities](features/ffo-host-dut-utilities.md) | SSH, regex, host utils |
| [ffo-test-suites](features/ffo-test-suites.md) | Suites and lifecycle |
| [ffo-extensions-plugins](features/ffo-extensions-plugins.md) | Plugins |

### Detailed Design

| DDD | Topic |
|-----|--------|
| [ddd-core-package-layout](design/ddd-core-package-layout.md) | Core package layout |
| [ddd-runtime-context](design/ddd-runtime-context.md) | Runtime context |
| [ddd-configuration](design/ddd-configuration.md) | Configuration |
| [ddd-output-artifacts](design/ddd-output-artifacts.md) | Output artifacts |
| [ddd-logging](design/ddd-logging.md) | Logging |
| [ddd-database](design/ddd-database.md) | SQLite |
| [ddd-measurement-verification](design/ddd-measurement-verification.md) | Decorators |
| [ddd-results-exit-codes](design/ddd-results-exit-codes.md) | Results / exit codes |
| [ddd-cli-runner](design/ddd-cli-runner.md) | CLI runner |
| [ddd-plugin-registry](design/ddd-plugin-registry.md) | Plugin registry |
| [ddd-suite-orchestration](design/ddd-suite-orchestration.md) | Suite runner |
| [ddd-setup-teardown](design/ddd-setup-teardown.md) | Setup / teardown |
| [ddd-database-read-api](design/ddd-database-read-api.md) | DB read helpers |
| [ddd-equipment-architecture](design/ddd-equipment-architecture.md) | Equipment architecture |
| [ddd-equipment-transports](design/ddd-equipment-transports.md) | VISA / serial |
| [ddd-equipment-scpi](design/ddd-equipment-scpi.md) | SCPI |
| [ddd-equipment-dmm-psu](design/ddd-equipment-dmm-psu.md) | DMM / PSU |
| [ddd-shared-architecture](design/ddd-shared-architecture.md) | Shared architecture |
| [ddd-shared-ssh-regex](design/ddd-shared-ssh-regex.md) | SSH / regex |
| [ddd-multiprocessing](design/ddd-multiprocessing.md) | Multiprocessing outline |

## Example Style

User-facing test scripts and guide snippets use one line per `col.*` call with keyword arguments inline. See [examples/](../examples/).
