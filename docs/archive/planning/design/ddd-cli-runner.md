# DDD: CLI Runner

> **Archived planning document.** For current behavior see [scope.md](../../../scope.md), Sphinx user guides, examples, and the codebase. Wave references below are historical only.


## Responsibilities

Provide `colosseum` console script: `run` (Wave 1), `run-suite` (Wave 3), argument parsing, context init, test module execution, exit code propagation.

## Public API surface

```bash
colosseum --gui
colosseum run <test.py> [--config PATH] [--verbose]
colosseum run-suite <suite.toml> [--config PATH] [--verbose]  # Wave 3
```

```python
# colosseum/runner/cli.py
def main(argv: Optional[List[str]] = None) -> None:
    sys.exit(run_cli(argv))
```

## `run` implementation

1. Parse args; resolve paths relative to CWD
2. If `--config`: `load_config(path)` (initializes context internally per [ddd-runtime-context.md](ddd-runtime-context.md))
3. Else: internal `init_context(test_case_name=stem, config_path=None)` only
4. Lazy `setup_logging` when output dir is first ensured (on first persist)
5. Ensure the output directory and execute the test module with `runpy.run_path(..., run_name="colosseum.test_run")`
6. Require a callable `main()` and call it; the script's `if __name__ == "__main__"` block is not executed by the CLI
7. Mark uncaught script exceptions as suite errors and call `endex()` in `finally`

## `--gui`

1. Parse `--gui` on the root parser (subcommands optional when `--gui` is set)
2. Lazy-import `colosseum.gui.app` (requires optional `colosseum[gui]` extra)
3. Launch CustomTkinter desktop runner; subprocesses to `run` / `run-suite` unchanged
4. Default bench config in GUI: file picker and `COLOSSEUM_BENCH_CONFIG` env var

## Direct Python parity

- Test script calls `col.config.load_config(...)` — same initialization path as CLI with `--config`
- Test scripts call `col.endex()` explicitly when not using CLI; runner invokes `endex()` in `finally`

## Data written

Delegates to output, logging, database subsystems.

## Sequence — happy path

```mermaid
sequenceDiagram
  participant Shell
  participant CLI
  participant Ctx
  participant Test
  Shell->>CLI: colosseum run test.py --config bench.toml
  CLI->>Ctx: init + load_config
  CLI->>Test: execute module
  Test->>Ctx: measurements/verifications
  CLI->>Shell: exit 0
```

## Sequence — config missing

```mermaid
sequenceDiagram
  participant CLI
  CLI->>CLI: load_config fails
  CLI->>CLI: exit 1
```

## Extension points

None.

## Open issues

- `--log-level DEBUG`: use `--verbose` mapping to DEBUG in v1.

## References

- [ddd-runtime-context.md](ddd-runtime-context.md)
- [ddd-suite-orchestration.md](ddd-suite-orchestration.md) (Wave 3)
- [ffo-single-test-execution.md](../features/ffo-single-test-execution.md)
