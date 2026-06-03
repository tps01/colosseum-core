# ADR-008: Output Directory Naming

> **Documentation note:** Normative behavior is in [mvp/scope.md](../mvp/scope.md), Sphinx user guides, and the codebase. Wave 1/2/3 references below are historical sequencing only.


## Status

Accepted

## Context

Open question §22 Q8: should direct Python execution and CLI produce identical output folder names?

## Decision

1. **Single function** `colosseum.output.allocate_run_directory(cwd, logical_name)` used by:
   - `col.config.load_config()` when it initializes runtime (lazy, on first artifact need)
   - `colosseum run` / `colosseum run-suite` CLI

2. **Pattern:** `outputs/<YYYY-MM-DD_HHMMSS>_<sanitized_logical_name>/`
   - `logical_name` = test file stem (e.g. `test_power_rails`) or suite `name` from TOML
   - Sanitize: alphanumeric, underscore, hyphen; max length 64

3. **CWD:** Output root is always `Path.cwd() / "outputs"` at time of allocation (architecture §9).

4. **Lazy creation:** Directory created on first log line or DB init, whichever comes first.

5. **Direct Python without `load_config`:** If user invokes APIs that need persistence without loading config, runtime allocates using test file `__main__` name or `"run"`.

6. **Suite run:** One directory named after suite `name`, not per-test subfolders (per ADR-004).

## Consequences

- Comparisons between `python test.py` and `colosseum run test.py` show same folder naming when `logical_name` matches.
- Multiprocessing / parallel DUT: each process calls allocate with distinct suffix (post-MVP; see D20).

## References

- [ddd-output-artifacts.md](../design/ddd-output-artifacts.md)
- [ffo-single-test-execution.md](../features/ffo-single-test-execution.md)
- Architecture §9
