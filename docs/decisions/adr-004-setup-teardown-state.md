# ADR-004: Setup and Teardown Execution State

> **Documentation note:** Normative behavior is in [mvp/scope.md](../mvp/scope.md), Sphinx user guides, and the codebase. Wave 1/2/3 references below are historical sequencing only.


## Status

Accepted

## Context

Open question §22 Q4: how setup/teardown share state with tests—separate DBs, folders, or shared artifacts?

## Decision

1. **One output directory per suite run** (or per single test run for Wave 1).

   Naming: `outputs/<timestamp>_<suite_or_test_name>/`

2. **One `execution.sqlite` per run** shared by setup, all test cases, and teardown in that suite execution.

3. **Phase tracking** via `run_metadata` keys:
   - `phase` = `setup` | `test` | `teardown`
   - `active_script` = path of current script
   - `suite_name`, `test_index`, etc. as applicable

4. **Events table** records phase transitions (`source=runner`, `message=phase_enter:setup`, etc.).

5. **Measurements and verifications** from setup/teardown use the same decorators and tables; domain/command fields distinguish origin.

6. **Single-test CLI (`colosseum run`):** No setup/teardown unless added later per-file; phase is `test` only.

7. **Failure:** Setup failure aborts test list, marks run ERROR, exit `1`. Teardown still attempted unless setup prevented runner init (implementation: always attempt teardown if suite started).

## Consequences

- Auditors see one SQLite file per suite invocation.
- Parallel suite runs remain separate processes with separate output dirs (post-MVP parallel execution).

## References

- [ddd-suite-orchestration.md](../design/ddd-suite-orchestration.md)
- [ddd-setup-teardown.md](../design/ddd-setup-teardown.md)
- [ffo-test-suites.md](../features/ffo-test-suites.md)
- Architecture §17
