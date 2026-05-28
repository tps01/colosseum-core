# FFO: Single Test Execution

## Summary

Users run one Python test case file—either directly with the Python interpreter or via the `colosseum run` CLI—and Colosseum initializes runtime state, executes user code, aggregates verification results, and exits with `0` or `1`.

## Actors

- Test engineer (author/runner)
- CI job invoking CLI

## Preconditions

- Python 3.9+ on Windows or Linux
- Test file imports `colosseum as col` (recommended)
- For instrumented tests (Wave 2+): `col.config.load_config(path)` or `--config` on CLI
- Bench may already be prepared (no mandatory setup in Wave 1)

## Main flow

1. User starts execution:
   - **Direct:** `python tests/test_power_rails.py`
   - **CLI:** `colosseum run tests/test_power_rails.py --config configs/bench.toml`
2. Colosseum initializes global runtime context via `col.config.load_config(...)` (direct Python) or the runner with optional `--config` — not a separate public init API ([ddd-runtime-context.md](../design/ddd-runtime-context.md)).
3. On first persistence need, Colosseum allocates `outputs/<timestamp>_<test_stem>/` per [ADR-008](../decisions/adr-008-output-naming.md).
4. User script runs: optional config load, equipment interaction, measurements, verifications, cleanup.
5. Each measurement/verification is logged and stored (see [ffo-measurements-verifications.md](ffo-measurements-verifications.md)).
6. At process exit, aggregate verification status determines exit code (see [ffo-measurements-verifications.md](ffo-measurements-verifications.md)).
7. CLI returns same exit code to shell; direct Python calls `col.endex()` to flush artifacts and `sys.exit(0|1)`.

## Outputs

| Artifact | Wave | Description |
|----------|------|-------------|
| `outputs/.../debug.log` | 1 | Run header + execution log |
| `outputs/.../execution.sqlite` | 1 | Measurements, verifications, metadata |
| Process exit code | 1 | `0` pass, `1` otherwise |

## Failure modes

| Condition | Verification/result | Exit code |
|-----------|---------------------|-----------|
| Required verification FAIL | FAIL recorded | `1` |
| Required verification ERROR (e.g. missing measurement) | ERROR recorded | `1` |
| Optional verification FAIL/ERROR | Recorded, marked optional | `0` if all required pass |
| Uncaught exception in test | ERROR event; run ERROR | `1` |
| Config load failure | No test execution; ERROR | `1` |

`SKIP` does not fail aggregate in v1 unless later configured.

## Exit code impact

Only required verification FAIL/ERROR and framework/runtime failures yield exit `1`. Optional verifications excluded per architecture §12.5.

## Non-goals (this feature)

- Suite orchestration ([ffo-test-suites.md](ffo-test-suites.md))
- Setup/teardown scripts
- `summary.txt` (Wave 3)
- Parallel test cases
- Context-manager `with col.run(...)` API

## Related design

- [ddd-runtime-context.md](../design/ddd-runtime-context.md)
- [ddd-cli-runner.md](../design/ddd-cli-runner.md)
- [ddd-results-exit-codes.md](../design/ddd-results-exit-codes.md)
- [scope.md](../mvp/scope.md) Wave 1
