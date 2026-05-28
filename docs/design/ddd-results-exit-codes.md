# DDD: Result Aggregation and Exit Codes

## Responsibilities

Track verification outcomes during run, compute overall pass/fail, map to process exit code `0`/`1`, and drive end-of-run reporting via `endex()`. Test scripts **must not** manually scan `read_verifications()` to decide pass/fail or exit code.

## Public API surface

```python
class ResultAggregator:
    def record_verification(self, result: VerificationResult) -> None
    def overall_pass(self) -> bool
    def counts(self) -> dict  # by status, split optional/required
    def exit_code(self) -> int  # 0 or 1

def endex() -> NoReturn:
    """
    1. Finalize result aggregation (required vs optional verifications)
    2. Write run_metadata overall_status / exit_code
    3. Write summary.txt (Wave 3) from aggregator counts and failed required rows
    4. Flush debug.log, close DB and bench connections
    5. sys.exit(aggregator.exit_code())
    """
```

Exported for direct-Python tests:

```python
import colosseum as col

if __name__ == "__main__":
    main()
    col.endex()  # aggregation + reporting + exit; does not return
```

## Aggregation rules

- **Required** verification with FAIL or ERROR → overall fail
- **Optional** verification FAIL/ERROR → recorded and reported; does not affect exit code
- SKIP → does not fail overall (v1)
- Uncaught framework exception → fail

`@verification` decorators call `record_verification` on each invoke; aggregation is always current before `endex()`.

## Reporting in `endex()`

| Output | Wave | Source |
|--------|------|--------|
| `run_metadata.overall_status` | 1 | `overall_pass()` |
| `run_metadata.exit_code` | 1 | `exit_code()` |
| `summary.txt` | 3 | Counts + list of failed required verifications (key, command, message) |
| `debug.log` tail | 1 | One-line overall result before shutdown |

Failed required verifications are already in `execution.sqlite`; `summary.txt` summarizes them for humans. No test-script loop required.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | `overall_pass()` true |
| 1 | otherwise |

No finer-grained exit codes in v1.

## What test authors should not do

```python
# Anti-pattern — do not gate exit this way
for record in col.database.read_verifications():
    if record.status != "PASS":
        raise AssertionError(...)
```

Use `col.endex()` instead. `read_verifications()` is for optional post-run inspection, CI artifact parsing, or interactive debug ([ddd-database-read-api.md](ddd-database-read-api.md)).

## Sequence — end of test

```mermaid
sequenceDiagram
  participant Test
  participant V as verify APIs
  participant Agg as ResultAggregator
  participant End as endex
  participant Sum as summary.txt
  Test->>V: verify_match FAIL required
  V->>Agg: record_verification
  Test->>End: endex
  End->>Agg: overall_pass false
  End->>Sum: write failed rows
  End->>End: sys.exit 1
```

## Extension points

None; core-only.

## Open issues

- Treat SKIP as failure for named tests: post-MVP config.

## References

- [ADR-010](../decisions/adr-010-endex.md)
- [ffo-single-test-execution.md](../features/ffo-single-test-execution.md)
- [ffo-measurements-verifications.md](../features/ffo-measurements-verifications.md)
- [ddd-output-artifacts.md](ddd-output-artifacts.md)
