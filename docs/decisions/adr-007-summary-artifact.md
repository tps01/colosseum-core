# ADR-007: Summary Artifact Generation

## Status

Accepted

## Context

Open question §22 Q7: should `summary.txt` be written continuously or once at end?

## Decision

1. **Wave 1:** No `summary.txt` (only `debug.log` and `execution.sqlite` minimum).

2. **Wave 3:** Generate `summary.txt` **once at end of run** (after last test or after teardown completes in suite mode).

3. **Content (minimum):**
   - Colosseum version, test/suite name, config path, output dir, start/end time
   - Counts: measurements, verifications by status (PASS/FAIL/ERROR/SKIP)
   - Overall result and exit code implication
   - List of failed required verifications (key, command, message)
   - Optional verifications listed separately with status

4. **`summary.json`:** Deferred post-MVP.

5. **Crash mid-run:** If process aborts without normal shutdown, `summary.txt` may be absent; `debug.log` and partial SQLite remain authoritative.

## Consequences

- Runner calls `SummaryWriter.write()` from `endex()` before `sys.exit`.
- No file watcher or incremental summary updates in v1.

## References

- [ddd-output-artifacts.md](../design/ddd-output-artifacts.md)
- [ffo-execution-evidence.md](../features/ffo-execution-evidence.md)
- Architecture §9
