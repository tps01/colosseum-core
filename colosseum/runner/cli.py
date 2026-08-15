from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from ..config import ConfigError, load_config
from ..context import init_context
from ..output import ensure_runtime_ready
from ..results import endex
from .single_test import ScriptRunError, run_script
from .suite import SuiteError, run_suite

_DESCRIPTION = (
    "Colosseum test automation: run Python test scripts and suites with bench configuration."
)
_EPILOG = """examples:
  colosseum run my_test.py --config bench.toml
  colosseum run my_test.py --autoconfig --autoconfig-export bench.generated.toml
  colosseum run-suite suite.toml --config bench.toml -d
  colosseum run-suite suite.toml --autoconfig --autoconfig-blacklist "Ethernet 1,192.168.1.10"
  colosseum --gui
"""


@dataclass(frozen=True)
class RunConfigOptions:
    """Bench configuration source for ``run`` / ``run-suite``."""

    config_path: str | None = None
    use_autoconfig: bool = False
    autoconfig_export: str | None = None
    autoconfig_blacklist: list[str] | None = None


def parse_autoconfig_blacklist(value: str | None) -> list[str] | None:
    """Split a comma-separated CLI blacklist into trimmed entries."""
    if value is None:
        return None
    entries = [part.strip() for part in value.split(",") if part.strip()]
    return entries or None


def _add_common_run_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--config",
        dest="config_path",
        metavar="PATH",
        help="Bench TOML config (equipment, shared, io sections)",
    )
    group.add_argument(
        "--autoconfig",
        action="store_true",
        help="Scan VISA resources and build bench config (requires colosseum-equipment[hardware])",
    )
    parser.add_argument(
        "--autoconfig-export",
        dest="autoconfig_export",
        metavar="PATH",
        help="Write autoconfig-generated bench TOML to PATH (requires --autoconfig)",
    )
    parser.add_argument(
        "--autoconfig-blacklist",
        dest="autoconfig_blacklist",
        metavar="LIST",
        help="Comma-separated interface names or local IPv4 addresses to exclude from TCPIP scan",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Include DEBUG logs on stdout",
    )
    parser.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Skip outputs/, debug.log, and on-disk execution.sqlite (utility/script mode)",
    )


def _run_config_options(args: argparse.Namespace) -> RunConfigOptions:
    if (args.autoconfig_export or args.autoconfig_blacklist) and not args.autoconfig:
        raise argparse.ArgumentTypeError(
            "--autoconfig-export and --autoconfig-blacklist require --autoconfig"
        )
    blacklist = parse_autoconfig_blacklist(getattr(args, "autoconfig_blacklist", None))
    return RunConfigOptions(
        config_path=args.config_path,
        use_autoconfig=bool(getattr(args, "autoconfig", False)),
        autoconfig_export=getattr(args, "autoconfig_export", None),
        autoconfig_blacklist=blacklist,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="colosseum",
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--gui", action="store_true", help="Launch the desktop GUI runner")
    sub = parser.add_subparsers(dest="command", required=False)

    run_parser = sub.add_parser(
        "run",
        help="Run a single Python test file",
        description="Initialize runtime, call the script's main(), and finalize with col.endex().",
    )
    run_parser.add_argument("test_file", help="Path to the Python test script")
    _add_common_run_options(run_parser)

    suite_parser = sub.add_parser(
        "run-suite",
        help="Run a suite TOML (setup, tests, teardown)",
        description=(
            "Run setup scripts, test scripts, and teardown scripts in one output directory."
        ),
    )
    suite_parser.add_argument("suite_file", help="Path to the suite TOML file")
    _add_common_run_options(suite_parser)

    help_parser = sub.add_parser(
        "help",
        help="Show help for colosseum or a subcommand",
        description="Print usage for colosseum or a specific subcommand.",
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        choices=("run", "run-suite"),
        help="Subcommand to describe (default: top-level usage)",
    )
    return parser


def _print_help(parser: argparse.ArgumentParser, topic: str | None = None) -> None:
    if topic is None:
        parser.print_help()
        return
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparser = action.choices.get(topic)
            if subparser is not None:
                subparser.print_help()
                return
    parser.error(f"unknown help topic: {topic}")


def _load_run_config(options: RunConfigOptions) -> None:
    if options.use_autoconfig:
        from ..context import require_context
        from ..plugins.loader import ensure_plugins_loaded

        ctx = require_context()
        ensure_plugins_loaded(ctx.plugin_registry)
        if not ctx.plugin_registry.has_namespace("equipment"):
            raise ConfigError(
                "Namespace `equipment` is not registered. Install colosseum-equipment "
                "and ensure it exposes a colosseum.plugins entry point."
            )
        from colosseum import equipment

        equipment.autoconfig(
            export_path=options.autoconfig_export,
            blacklist=options.autoconfig_blacklist,
        )
    elif options.config_path:
        load_config(options.config_path)


def _run_single_test(
    test_path: Path,
    options: RunConfigOptions,
    debug: bool,
    *,
    no_artifacts: bool = False,
) -> None:
    config_path = options.config_path
    ctx = init_context(
        test_case_name=test_path.stem,
        config_path=Path(config_path).resolve() if config_path else None,
        no_artifacts=no_artifacts,
    )
    ctx.debug_logging = debug
    _load_run_config(options)
    ensure_runtime_ready(ctx)
    try:
        run_script(test_path)
    except ScriptRunError:
        ctx.result_aggregator.mark_suite_error("test script failed")
    finally:
        endex()


def run_cli(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.gui:
        from ..gui.app import main as gui_main

        gui_main()
        return 0

    if args.command is None:
        _print_help(parser)
        return 0

    if args.command == "help":
        _print_help(parser, getattr(args, "topic", None))
        return 0

    try:
        run_options = _run_config_options(args)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    if args.command == "run":
        test_path = Path(args.test_file).resolve()
        if not test_path.exists():
            raise SystemExit(1)
        try:
            _run_single_test(
                test_path,
                run_options,
                bool(args.debug),
                no_artifacts=bool(getattr(args, "no_artifacts", False)),
            )
        except ConfigError:
            raise SystemExit(1) from None
        return 0

    if args.command == "run-suite":
        suite_path = Path(args.suite_file).resolve()
        if not suite_path.exists():
            raise SystemExit(1)
        try:
            config = Path(run_options.config_path).resolve() if run_options.config_path else None
            run_suite(
                suite_path,
                config,
                debug=bool(args.debug),
                use_autoconfig=run_options.use_autoconfig,
                autoconfig_export=(
                    Path(run_options.autoconfig_export).resolve()
                    if run_options.autoconfig_export
                    else None
                ),
                autoconfig_blacklist=run_options.autoconfig_blacklist,
                no_artifacts=bool(getattr(args, "no_artifacts", False)),
            )
        except (ConfigError, SuiteError):
            raise SystemExit(1) from None
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
