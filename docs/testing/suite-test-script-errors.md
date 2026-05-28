# Suite behavior when a test script raises

## Current behavior (v1)

When a script in the suite **`tests`** list raises an uncaught exception:

1. The runner logs a `script_fail:...` event and continues with remaining tests.
2. Teardown still runs.
3. The aggregate result **does not** automatically fail unless a required verification recorded `FAIL`/`ERROR`, or setup/teardown failed.

Therefore a suite can exit **`0`** even when a test script crashed without recording verifications.

This is covered by `tests/integration/test_suite_runner.py::test_test_script_exception_does_not_fail_suite_without_verification`.

## Rationale

Historical MVP choice: treat script exceptions like logged faults while keeping suite throughput; setup/teardown and verification evidence remain the primary pass/fail signals. See [docs/mvp/scope.md](../mvp/scope.md) (“Suite test exceptions”).

## Post-MVP option

A suite flag such as `continue_on_test_failure = false` could mark any test `ScriptRunError` as a required suite error. See [ddd-setup-teardown.md](../design/ddd-setup-teardown.md).
