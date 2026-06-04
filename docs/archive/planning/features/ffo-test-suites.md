# FFO: Test Suites and Lifecycle

> **Archived planning document.** For current behavior see [scope.md](../../../scope.md), Sphinx user guides, examples, and the codebase. Wave references below are historical only.


## Summary

Users define ordered collections of test case files with optional setup and teardown scripts in TOML. The `colosseum run-suite` CLI runs them in sequence, sharing one output directory and one execution database per suite invocation.

## Actors

- Test engineer
- CI pipeline running acceptance suites

## Preconditions

- Suite TOML exists with `name` and `tests` list
- Config available via `--config`
- Paths in suite file resolve relative to suite file location or CWD (implementation: suite file directory per DDD)

## Main flow

1. User runs `colosseum run-suite suites/smoke.toml --config configs/bench.toml`.
2. Runner loads suite TOML; allocates output dir named after suite `name` ([ADR-008](../decisions/adr-008-output-naming.md)).
3. **Setup phase:** For each path in `setup`, run Python script with phase metadata ([ADR-004](../decisions/adr-004-setup-teardown-state.md)).
4. **Test phase:** Run each test file in `tests` order; update `test_index` metadata.
5. **Teardown phase:** Run each `teardown` script even if tests failed (unless init failed).
6. Write `summary.txt` at end ([ADR-007](../decisions/adr-007-summary-artifact.md)).
7. Exit `0` or `1` from aggregate verifications across all phases.

## Suite TOML example

```toml
name = "smoke_acceptance"

setup = [
  "setup/flash_firmware.py",
  "setup/prepare_bench.py",
]

tests = [
  "tests/test_power_rails.py",
  "tests/test_boot.py",
]

teardown = [
  "teardown/collect_logs.py",
  "teardown/power_down.py",
]
```

## Outputs

Single `outputs/<timestamp>_<suite_name>/` with shared `execution.sqlite`, `debug.log`, `summary.txt`.

## Failure modes

| Condition | Behavior |
|-----------|----------|
| Setup script failure | Abort tests; ERROR; attempt teardown |
| Test failure (required verify) | Continue remaining tests (v1); overall fail |
| Teardown failure | Log ERROR; exit `1` (v1 policy) |
| Missing test file | ERROR before run |

## Exit code impact

Any required verification FAIL/ERROR in any phase, setup failure, or teardown failure (v1) → exit `1`.

## Non-goals

- Parallel test execution within suite
- Test filtering / tags
- Retry policies
- Per-test separate output folders

## Related design

- [ddd-suite-orchestration.md](../design/ddd-suite-orchestration.md)
- [ddd-setup-teardown.md](../design/ddd-setup-teardown.md)
- [ADR-004](../decisions/adr-004-setup-teardown-state.md)
