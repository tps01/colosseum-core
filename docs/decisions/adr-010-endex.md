# ADR-010: End-of-Run API Name (`endex`)

## Status

Accepted

## Context

Direct-Python test scripts and the CLI need a single end-of-run entry point to flush logs, close the database, write `summary.txt` (Wave 3), and exit with `0` or `1`. Draft docs used `finalize_run` and `finalize_and_exit`.

## Decision

The public API is **`col.endex()`** (implemented in `colosseum`, re-exported for `import colosseum as col`).

Behavior:

1. Finalize **result aggregation** (required vs optional verifications already recorded by decorators)
2. Write `run_metadata` overall status and exit code; write `summary.txt` when applicable (Wave 3)
3. Flush logging and close `execution.sqlite`
4. Close instrument/SSH connections held on the runtime context
5. `sys.exit(0)` if overall pass, else `sys.exit(1)`

Test scripts must not loop `read_verifications()` or raise `AssertionError` to gate exit — that is `endex()`'s job.

`endex()` does not return (`NoReturn`). The CLI runner calls it from a `finally` block after executing the test or suite.

## Consequences

- Examples and user docs use `col.endex()` only.
- No separate `finalize_run` / `finalize_and_exit` names.

## References

- [ddd-results-exit-codes.md](../design/ddd-results-exit-codes.md)
- [examples/test_power_rails.py](../../examples/test_power_rails.py)
