# Suite behavior when a test script raises

## Output model

Each script in a suite runs in its own child folder under the suite container.
Only **test** slot results determine suite pass/fail by default. Setup,
`between_tests`, and teardown slots keep their own logs and optional SQLite
evidence but do not affect the suite outcome unless `fail_fast = true` records
session-level `suite_failed`.

## Default behavior (`fail_fast = false`)

When a script in the suite **`tests`** list raises an uncaught exception:

1. The runner logs a `script_fail:...` event in that test slot's database.
2. The test slot is finalized as FAIL; later tests and teardown still run.
3. The suite container summary reports FAIL if any test slot failed.

Therefore a suite exits **`1`** when a test script crashes without recording
verifications.

This is covered by
`tests/integration/test_suite_runner.py::test_test_script_exception_fails_suite_without_verification`.

When a test entry uses **`repeat_count`** or **`repeat_for`**, a failed
iteration does not stop later iterations of that entry unless `fail_fast = true`.
Failures accumulate across the soak window.

Supporting-script failures (setup, `between_tests`, teardown) are logged in
their slot folders and the suite **continues**.

## Rationale

The default preserves suite throughput and teardown execution. Test-script
failures still fail the suite because the script did not complete its evidence
path. See [docs/scope.md](../scope.md).

## `fail_fast = true`

When continuing after a failure would be dangerous, set in the suite TOML:

```toml
fail_fast = true
```

Then the runner stops remaining **setup / between / test** work after:

- an uncaught script exception / early exit, or
- a required verification or command FAIL/ERROR after a script returns

**Every** teardown script still runs (a failing teardown does not skip later
teardown scripts). The suite fails via session `suite_failed`. Optional
failures do not stop the suite.

Covered by `tests/integration/test_suite_runner.py` and
`tests/e2e/test_suite_cli.py` fail-fast cases (including setup abort and
multi-teardown continuation).
