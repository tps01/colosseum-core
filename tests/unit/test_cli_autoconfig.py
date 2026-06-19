"""Unit tests for CLI autoconfig flags."""

from __future__ import annotations

import argparse

import pytest
from colosseum.runner.cli import (
    _build_parser,
    _run_config_options,
    parse_autoconfig_blacklist,
    run_cli,
)


def test_parse_autoconfig_blacklist_splits_commas() -> None:
    assert parse_autoconfig_blacklist("eth0, 192.168.1.10") == ["eth0", "192.168.1.10"]
    assert parse_autoconfig_blacklist("") is None
    assert parse_autoconfig_blacklist(None) is None


def test_config_and_autoconfig_are_mutually_exclusive() -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["run", "test.py", "--config", "bench.toml", "--autoconfig"]
        )


def test_autoconfig_export_requires_autoconfig_flag() -> None:
    parser = _build_parser()
    args = parser.parse_args(["run", "test.py", "--autoconfig-export", "out.toml"])
    with pytest.raises(argparse.ArgumentTypeError):
        _run_config_options(args)


def test_run_config_options_parses_autoconfig_flags() -> None:
    parser = _build_parser()
    args = parser.parse_args(
        [
            "run",
            "test.py",
            "--autoconfig",
            "--autoconfig-export",
            "bench.generated.toml",
            "--autoconfig-blacklist",
            "Ethernet 1,192.168.1.10",
        ]
    )
    options = _run_config_options(args)
    assert options.use_autoconfig is True
    assert options.config_path is None
    assert options.autoconfig_export == "bench.generated.toml"
    assert options.autoconfig_blacklist == ["Ethernet 1", "192.168.1.10"]


def test_run_config_options_rejects_export_without_autoconfig() -> None:
    parser = _build_parser()
    args = parser.parse_args(["run", "test.py", "--autoconfig-export", "out.toml"])
    with pytest.raises(argparse.ArgumentTypeError):
        _run_config_options(args)


def test_run_cli_help_exits_zero() -> None:
    assert run_cli(["help"]) == 0
