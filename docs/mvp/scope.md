# Colosseum MVP Scope and Success Criteria

## Purpose

This document is the canonical boundary for the Colosseum minimum viable product (MVP). It defines what ships in each wave, what is deferred, and how success is judged. Detailed behavior lives in [feature functional overviews](../features/) and [detailed design documents](../design/). Architecture background is in [scratchpad/colosseum_architecture_document.md](../../scratchpad/colosseum_architecture_document.md).

## Product summary

Colosseum is a Python-importable, offline, plugin-oriented test automation framework for embedded system integration and acceptance testing on the bench. Users write ordinary Python test scripts that call high-level APIs (`import colosseum as col`), load TOML bench configuration, perform measurements and verifications, and produce local execution evidence (logs, SQLite, summaries).

## Compatibility matrix (all waves)

| Requirement | MVP commitment |
|-------------|----------------|
| Python | 3.9+ |
| Platforms | Windows and Linux |
| Network | Offline by default; no cloud dependency |
| User import | `import colosseum as col` |
| Documentation generation | Sphinx from docstrings (implementation task, not a separate DDD) |

## Distribution split

| Distribution | Package import | User namespace | Key dependencies |
|--------------|----------------|----------------|------------------|
| `colosseum` | `colosseum` | `col.config`, `col.database`, core decorators, runner | `tomli` on Python &lt; 3.11 |
| `colosseum-equipment` | `colosseum_equipment` (plugin) | `col.equipment.*` | `pyserial`, `pyvisa` |
| `colosseum-shared` | `colosseum_shared` (plugin) | `col.shared.*` | `paramiko` |

See [ADR-001](../decisions/adr-001-distributions.md).

## Phased MVP

### Wave 1 — Core runnable test

**User-visible outcome:** Load config, run a single test file (direct Python or `colosseum run`), persist measurements/verifications to `outputs/<timestamp>_<test>/`, exit `0` or `1`.

**In scope:**

- Global runtime context
- TOML configuration load and normalization (single table vs array-of-tables)
- `@measurement` and `@verification` decorators
- Result states: PASS, FAIL, ERROR, SKIP
- Measurement key uniqueness (per command/domain rules)
- Optional verifications (`optional=True`)
- Lazy `outputs/` directory creation
- Core SQLite schema and `debug.log` with run header metadata
- CLI: `colosseum run <test.py> --config <bench.toml>`
- Identical output directory naming for CLI and direct Python (when runtime is initialized)

**Deferred from Wave 1:**

- Suites, setup/teardown
- First-party equipment/shared beyond plugin stubs (if any)
- Vendor-specific SCPI
- `summary.txt`
- Public database read helpers
- Multiprocessing worker patterns
- Context-manager runtime API

**Related docs:** FFO F1–F4; DDD D1–D3, D5–D10.

### Wave 2 — Bench adaptation

**User-visible outcome:** Architecture doc example flows work: PSU/DMM via VISA, serial, SSH measure + regex verify, raw SCPI/transport escape hatches.

**In scope:**

- `colosseum-equipment` and `colosseum-shared` as plugins (same registration as third-party)
- Transport / protocol / instrument layering
- Generic DMM and PSU high-level APIs backed by generic SCPI
- pyserial, pyvisa, paramiko integration
- Optional verifications (full behavior per architecture)

**Deferred from Wave 2:**

- Vendor-specific EDU34450A and Genesys implementations (Wave 3)
- Parallel suite/DUT execution
- Formal plugin namespace collision policy (warn + last-wins for v1)

**Related docs:** FFO F5, F6, F8; DDD D4, D14–D19.

### Wave 3 — Suite orchestration and reference instruments

**User-visible outcome:** `colosseum run-suite`, setup/teardown scripts, `summary.txt`, reference DMM/PSU drivers, database read helpers.

**In scope:**

- Suite TOML (`name`, `setup`, `tests`, `teardown`)
- Setup failure → ERROR, exit `1`; teardown failure → exit `1` (v1)
- `summary.txt` at end of run only
- Keysight EDU34450A and TDK-Lambda Genesys behind same high-level APIs
- `col.database.read_*` helpers (typed records, no pandas)

**Deferred from Wave 3 (post-MVP):**

- Context-manager runtime API
- Test generation, HTML/JUnit/Allure, ALM integrations
- Config JSON-schema validation
- Stable public SQLite schema guarantee
- Parallel suite execution, GUI runner, retry policies
- Rich CLI filtering
- `summary.json`
- SKIP-as-failure configuration

**Related docs:** FFO F7; DDD D11–D13, D17 vendor sections; D20 outline.

## Success scenarios

### Wave 1 done

1. **Direct Python:** User runs `python tests/test_stub.py` after `col.config.load_config("bench.toml")`. Script registers at least one measurement and one verification (may use core test doubles or minimal built-ins). `outputs/` contains `debug.log` and `execution.sqlite`. Process exit code reflects verification aggregate.
2. **CLI:** `colosseum run tests/test_stub.py --config configs/bench.toml` produces the same output layout and exit semantics as (1).
3. **Failure path:** Missing measurement key for a required verification yields ERROR in DB, overall FAIL, exit `1`.
4. **Optional verify:** `optional=True` failure does not change exit code from pass.

### Wave 2 done

1. **Power rail check:** Config defines PSU and DMM; test enables output, measures voltage, verifies within tolerance; results in SQLite.
2. **SSH version check:** `col.shared.ssh.measure_stdout` + `col.shared.regex.verify_match` on configured target.
3. **Escape hatch:** User sends raw SCPI via `col.equipment.scpi.query` without bypassing logging/DB for wrapped calls.
4. **Plugin parity:** Third-party extension can register `col.myvendor.*` using the same entry point as equipment/shared.

### Wave 3 done

1. **Suite run:** `colosseum run-suite suites/smoke.toml --config configs/bench.toml` runs setup → tests → teardown in order; single output directory and one `execution.sqlite` with phase metadata.
2. **Summary:** `summary.txt` present after suite completes; reflects pass/fail counts and optional verifications.
3. **Reference instruments:** Bench with EDU34450A or Genesys can use model-specific driver selection in config while test script API unchanged.
4. **Read helpers:** `col.database.read_verifications()` returns typed list for inspection/tooling; exit code comes from `col.endex()`, not manual scans in test scripts.

## Documentation index

| Type | Location |
|------|----------|
| Architecture (source) | [scratchpad/colosseum_architecture_document.md](../../scratchpad/colosseum_architecture_document.md) |
| ADRs | [docs/decisions/](../decisions/) |
| Feature overviews | [docs/features/](../features/) |
| Detailed design | [docs/design/](../design/) |
| User guides (tracked, not yet written) | [mvp/user-documentation.md](user-documentation.md) |

## User-facing documentation (explicitly tracked, not MVP implementation docs)

Architecture §19 calls for Sphinx-generated **user** documentation: installation, quickstart, config syntax, running tests/suites, output layout, exit codes, API reference (autodoc), plugin development, Windows/Linux notes, and multiprocessing guidance.

The current `docs/` tree is **implementation planning** (scope, ADRs, FFOs, DDDs). That is intentional for this phase. User-facing deliverables are tracked in [user-documentation.md](user-documentation.md) with target wave and status; they are not blockers for Wave 1 coding.

`summary.txt` is deferred to Wave 3 per [ADR-007](../decisions/adr-007-summary-artifact.md) — not omitted from the product plan.

## Post-MVP capabilities (architecture §21)

The following are explicitly out of MVP scope but acknowledged in the architecture document:

- Context-managed runtime (`with col.run(...)`)
- Test generation and model-based testing
- Requirement traceability and ALM exports
- HTML reports, JUnit XML, Allure
- Configuration schema validation
- Stable public database schema versioning
- Web/desktop testing plugins
- Formal plugin collision handling (fail-fast / user selection)
- Parallel suite execution and GUI runner

## Deferred feature documentation

No separate FFOs for these in MVP; mention only here:

- Parallel DUTs and parallel test cases (§18.1) — separate output dirs per process
- In-test multiprocessing verification (§18.2) — see [ddd-multiprocessing.md](../design/ddd-multiprocessing.md) outline
- Context-manager runtime (§7)
