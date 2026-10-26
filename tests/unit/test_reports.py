"""Report listener enablement from config and CLI."""

from __future__ import annotations

from colosseum.config.loader import ConfigStore
from colosseum.results.reports import (
    apply_enabled_reports,
    resolve_enabled_reports,
    reports_from_config,
)
from colosseum.runner.run_options import RunOptions


def test_reports_default_empty(unit_runtime_context) -> None:
    assert reports_from_config(unit_runtime_context) == frozenset()
    assert resolve_enabled_reports(unit_runtime_context) == frozenset()


def test_reports_from_config_table(unit_runtime_context) -> None:
    unit_runtime_context.config = ConfigStore(
        {"colosseum": {"reports": {"wats": True, "junit": False, "custom": True}}},
        {},
        {},
    )
    assert reports_from_config(unit_runtime_context) == frozenset({"wats", "custom"})


def test_reports_accept_bool_spellings(unit_runtime_context) -> None:
    unit_runtime_context.config = ConfigStore(
        {"colosseum": {"reports": {"wats": "T", "junit": "no", "custom": 1, "skip": "maybe"}}},
        {},
        {},
    )
    assert reports_from_config(unit_runtime_context) == frozenset({"wats", "custom"})


def test_cli_report_replaces_config(unit_runtime_context) -> None:
    unit_runtime_context.config = ConfigStore(
        {"colosseum": {"reports": {"wats": True, "junit": True}}},
        {},
        {},
    )
    unit_runtime_context.run_options = RunOptions(report_cli=["junit"])
    assert resolve_enabled_reports(unit_runtime_context) == frozenset({"junit"})


def test_apply_warns_unknown_listener(unit_runtime_context) -> None:
    warnings: list[str] = []

    class _Logger:
        def warning(self, msg: str, *args: object) -> None:
            warnings.append(msg % args if args else msg)

        def info(self, msg: str, *args: object) -> None:
            return None

    unit_runtime_context.logger = _Logger()  # type: ignore[assignment]
    unit_runtime_context.run_options = RunOptions(report_cli=["no_such_report"])
    apply_enabled_reports(unit_runtime_context)
    assert unit_runtime_context.enabled_reports == frozenset({"no_such_report"})
    assert any("no_such_report" in text for text in warnings)
