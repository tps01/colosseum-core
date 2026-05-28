# DDD: Multiprocessing Patterns (Outline)

## Status

Post-MVP outline per [scope.md](../mvp/scope.md). Not required for Waves 1–3 implementation.

## Responsibilities (future)

Document safe patterns for CPU-heavy verification work within one test case without sharing live handles across processes.

## Recommended pattern (architecture §18.2)

1. Perform measurement once in parent process
2. Save large data to artifact under output directory
3. Store `artifact_path` in SQLite
4. Spawn workers with pickleable arguments (paths, keys, thresholds only)
5. Workers return verification results as plain dicts/dataclasses
6. Parent merges into active `execution.sqlite` via `DatabaseManager.insert_verification`

## Constraints

- Do not pass: `RuntimeContext`, DB connections, loggers, VISA/serial/SSH sessions
- Each parallel **test case** or **DUT** uses separate output directory and SQLite file (§18.1)

## Public API surface (future)

```python
# Illustrative only — not MVP
col.parallel.verify_artifact_workers(...)
```

## Open issues

- Helper API design
- Worker pool sizing and Windows spawn semantics on 3.9

## References

- Architecture §18
- [scope.md](../mvp/scope.md) deferred capabilities
