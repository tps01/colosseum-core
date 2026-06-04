# Suite behavior when a test script raises

## Current behavior

When a script in the suite **`tests`** list raises an uncaught exception:

1. The runner logs a `script_fail:...` event and continues with remaining tests.
2. Teardown still runs.
3. The aggregate result is marked failed through a suite error.

Therefore a suite exits **`1`** when a test script crashes without recording verifications.

This is covered by `tests/integration/test_suite_runner.py::test_test_script_exception_fails_suite_without_verification`.

## Rationale

The runner preserves suite throughput and teardown execution, but an uncaught test exception is still a failed run because the script did not complete its evidence path. See [docs/scope.md](../scope.md) ("Suite test exceptions").

## Future option

A future suite flag could choose fail-fast behavior or opt into best-effort continuation semantics. See [ddd-setup-teardown.md](../design/ddd-setup-teardown.md).
