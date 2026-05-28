# Colosseum Documentation

Documentation for the Colosseum MVP, derived from [scratchpad/colosseum_architecture_document.md](../scratchpad/colosseum_architecture_document.md).

## Start here

1. [MVP scope and success criteria](mvp/scope.md)
2. [Architecture decisions](decisions/) (ADRs 001–009)
3. [Feature functional overviews](features/) (FFOs)
4. [Detailed design documents](design/) (DDDs)
5. [User documentation tracker](mvp/user-documentation.md) — installation, quickstart, Sphinx guides
6. [Sphinx user docs build](sphinx/README.md) — `scripts/docgen/` modular pipeline
7. [Testing and regression](testing/README.md) — pytest tiers 1–3, extended procedure

## Document map

### MVP

| Document | Description |
|----------|-------------|
| [mvp/scope.md](mvp/scope.md) | Waves 1–3 boundaries and success scenarios |
| [mvp/user-documentation.md](mvp/user-documentation.md) | User-facing Sphinx docs tracker (§19) |

### Decisions

| ADR | Topic |
|-----|--------|
| [adr-001](decisions/adr-001-distributions.md) | Distributions and namespace |
| [adr-002](decisions/adr-002-plugin-registration.md) | Plugin registration |
| [adr-003](decisions/adr-003-config-validation.md) | Config validation |
| [adr-004](decisions/adr-004-setup-teardown-state.md) | Setup/teardown state |
| [adr-005](decisions/adr-005-database-read-api.md) | DB read API shape |
| [adr-006](decisions/adr-006-vendor-instruments.md) | Vendor DMM/PSU |
| [adr-007](decisions/adr-007-summary-artifact.md) | summary.txt |
| [adr-008](decisions/adr-008-output-naming.md) | Output directory naming |
| [adr-009](decisions/adr-009-plugin-namespace-collisions.md) | Namespace collisions |
| [adr-010](decisions/adr-010-endex.md) | `endex()` end-of-run API |

### Features (FFO)

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

### Design (DDD)

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
| [ddd-multiprocessing](design/ddd-multiprocessing.md) | Multiprocessing (outline) |

## Suggested implementation order

See [mvp/scope.md](mvp/scope.md) and the MVP documentation plan: Wave 1 core DDDs (D1–D3, D5–D10) before Wave 2 equipment/shared, then Wave 3 suite and read API.

## Code style in examples

User-facing test scripts and documentation examples use **one line per `col.*` call** with keyword arguments inline (see [examples/](../examples/) and [examples/README.md](../examples/README.md)). Implementation signatures in DDDs may use multi-line `def` blocks; runnable test-style snippets should not wrap routine API calls across lines.
