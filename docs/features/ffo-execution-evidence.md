# FFO: Execution Evidence

## Summary

Every test or suite run produces local, offline artifacts for debugging and audit: structured logs, SQLite execution database, and (Wave 3) human-readable summary. Users and tools can inspect results without re-running the bench.

## Actors

- Test engineer (reviews `debug.log`, `summary.txt`)
- CI (archives `outputs/` directory)
- Advanced user (read helpers / SQLite)

## Preconditions

- Runtime initialized and at least one operation triggered persistence (log or DB)

## Main flow

1. First log or DB write triggers `outputs/<timestamp>_<name>/` creation ([ADR-008](../decisions/adr-008-output-naming.md)).
2. `debug.log` receives header block: Colosseum version, Python version, platform, test/suite name, config path, output path, start time.
3. Measurements, verifications, and events append to `execution.sqlite` during run.
4. Plugins may write additional files under output dir (flat by default; subdirs only when path includes subdirectory).
5. **Wave 3:** On normal completion, `summary.txt` written once ([ADR-007](../decisions/adr-007-summary-artifact.md)).
6. **Wave 3:** User may call `col.database.read_measurements()` etc. during or after run.

## Required artifacts

| File | Wave | Purpose |
|------|------|---------|
| `debug.log` | 1 | Human-readable trace |
| `execution.sqlite` | 1 | Structured measurements/verifications |
| `summary.txt` | 3 | End-of-run rollup |
| `measurement_trace.csv` | — | Only if a command/plugin creates it (not auto-created by core) |

## Database tables (conceptual)

- `run_metadata`, `measurements`, `verifications`, `events`, `artifacts`
- Plugin tables: `plugin_<name>_<table>` convention

## Failure modes

| Condition | Evidence |
|-----------|----------|
| Crash before DB init | May have no `outputs/` or partial log |
| Disk full | ERROR logged; run may abort |
| Read helper without active context | Clear error (MVP) |

## Exit code impact

Evidence capture does not change exit code; content reflects failures already counted.

## Non-goals

- Automatic upload to cloud
- Mandatory `artifacts/` or `reports/` subfolders
- `summary.json` in MVP
- Guaranteed schema immutability across versions

## Related design

- [ddd-output-artifacts.md](../design/ddd-output-artifacts.md)
- [ddd-logging.md](../design/ddd-logging.md)
- [ddd-database.md](../design/ddd-database.md)
- [ddd-database-read-api.md](../design/ddd-database-read-api.md)
- [ADR-005](../decisions/adr-005-database-read-api.md), [ADR-007](../decisions/adr-007-summary-artifact.md)
