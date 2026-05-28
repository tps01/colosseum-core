from __future__ import annotations

import argparse
from pathlib import Path
import runpy
import sys

from ..config import ConfigError, load_config
from ..context import init_context
from ..results import endex
from .suite import SuiteError, run_suite


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="colosseum")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a single Python test file")
    run_parser.add_argument("test_file")
    run_parser.add_argument("--config", dest="config_path")
    run_parser.add_argument("--verbose", action="store_true")

    suite_parser = sub.add_parser("run-suite", help="Run a suite TOML (setup, tests, teardown)")
    suite_parser.add_argument("suite_file")
    suite_parser.add_argument("--config", dest="config_path")
    suite_parser.add_argument("--verbose", action="store_true")
    return parser


def _run_single_test(test_path: Path, config_path: str | None, verbose: bool) -> None:
    ctx = init_context(
        test_case_name=test_path.stem,
        config_path=Path(config_path).resolve() if config_path else None,
    )
    ctx.verbose_logging = verbose
    if config_path:
        load_config(config_path)

    module_globals = runpy.run_path(str(test_path), run_name="colosseum.test_run")
    main_fn = module_globals.get("main")
    if not callable(main_fn):
        raise SystemExit(1)
    main_fn()
    endex()


def run_cli(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        test_path = Path(args.test_file).resolve()
        if not test_path.exists():
            raise SystemExit(1)
        try:
            _run_single_test(test_path, args.config_path, bool(args.verbose))
        except ConfigError:
            raise SystemExit(1)
        return 0

    if args.command == "run-suite":
        suite_path = Path(args.suite_file).resolve()
        if not suite_path.exists():
            raise SystemExit(1)
        try:
            config = Path(args.config_path).resolve() if args.config_path else None
            run_suite(suite_path, config, verbose=bool(args.verbose))
        except (ConfigError, SuiteError):
            raise SystemExit(1)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


def main(argv: list[str] | None = None) -> None:
    try:
        sys.exit(run_cli(argv))
    except SystemExit as exc:
        raise exc


if __name__ == "__main__":
    main()
