"""Manually replay a fuzz corpus under coverage.py; no randomized exploration."""

from __future__ import annotations

import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MODULES = {
    "disk_finalization": ("results/finalize.py", "summary/writer.py", "database/manager.py"),
    "suite_finalization": (
        "results/aggregation.py",
        "results/exit_policy.py",
        "runner/runtime.py",
        "summary/writer.py",
    ),
    "database": ("database/manager.py", "database/write_queue.py"),
    "results": ("results/aggregation.py",),
    "finalization": ("results/finalize.py", "results/exit_policy.py", "results/finalize_policy.py"),
}


def main() -> int:
    """Replay inputs once and write scoped branch/line reports for inspection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=MODULES)
    parser.add_argument("--corpus", type=Path, help="Default: tracked seeds for this target")
    parser.add_argument("--output", type=Path, help="Default: .fuzz-work/coverage/TARGET")
    args = parser.parse_args()
    seed_name = f"{args.target}_corpus"
    corpus = (args.corpus or REPO / "tests/fuzz" / seed_name).resolve()
    if not corpus.is_dir():
        parser.error(f"Corpus directory does not exist: {corpus}")
    inputs = sorted(str(path) for path in corpus.iterdir() if path.is_file())
    if not inputs:
        parser.error(f"Corpus directory has no inputs: {corpus}")
    output = (args.output or REPO / ".fuzz-work/coverage" / args.target).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Import the targets only after tracing starts. Their check_input functions
    # are shared with Atheris and pytest, but do not import the fuzzing engine.
    from importlib import import_module

    from coverage import Coverage

    include = [f"*/colosseum/{module}" for module in MODULES[args.target]]
    coverage = Coverage(
        data_file=str(output / ".coverage"),
        branch=True,
        concurrency=["thread"],
        include=include,
        config_file=False,
    )
    coverage.start()
    try:
        check = import_module(f"tests.fuzz.{args.target}").check_input
        check(b"")
        for filename in inputs:
            print(f"Replaying {filename}")
            check(Path(filename).read_bytes())
    finally:
        coverage.stop()
        coverage.save()
    coverage.json_report(outfile=str(output / "coverage.json"), pretty_print=True)
    coverage.html_report(directory=str(output / "html"))
    coverage.report(show_missing=True)
    print(f"Replayed {len(inputs)} corpus files plus the empty input. Reports: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
