"""Resolve enabled report listeners from config and CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from colosseum.config.toml_relaxed import coerce_config_bool

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext
    from colosseum.runner.run_options import RunOptions


def reports_from_config(ctx: RuntimeContext) -> frozenset[str]:
    """Return report names enabled in ``[colosseum.reports]``."""
    if ctx.config is None:
        return frozenset()
    section = ctx.config.get_section("colosseum.reports")
    if not isinstance(section, dict):
        return frozenset()
    enabled: set[str] = set()
    for name, value in section.items():
        key = str(name)
        enabled_flag = coerce_config_bool(value)
        if enabled_flag is not None:
            if enabled_flag:
                enabled.add(key)
            continue
        if ctx.logger is not None:
            ctx.logger.warning(
                "Unknown or non-boolean value for `[colosseum.reports].%s`; ignored",
                key,
            )
    return frozenset(enabled)


def resolve_enabled_reports(
    ctx: RuntimeContext,
    options: RunOptions | None = None,
) -> frozenset[str]:
    """CLI ``--report`` replaces the config table when any flag is present."""
    opts = options if options is not None else ctx.run_options
    if opts.report_cli is not None:
        return frozenset(opts.report_cli)
    return reports_from_config(ctx)


def warn_unknown_report_names(ctx: RuntimeContext, enabled: frozenset[str]) -> None:
    known = set(ctx.plugin_registry.listener_names())
    for name in sorted(enabled):
        if name not in known and ctx.logger is not None:
            ctx.logger.warning(
                "Report `%s` is enabled but no listener is registered; ignored",
                name,
            )


def apply_enabled_reports(ctx: RuntimeContext) -> None:
    ctx.enabled_reports = resolve_enabled_reports(ctx)
    warn_unknown_report_names(ctx, ctx.enabled_reports)
    if ctx.logger is not None and ctx.enabled_reports:
        ctx.logger.info("Enabled reports: %s", ", ".join(sorted(ctx.enabled_reports)))


def report_section_warnings(raw: dict[str, Any]) -> list[str]:
    """Validate ``[colosseum.reports]`` values; unknown names are OK (plugins)."""
    warnings: list[str] = []
    section = raw.get("colosseum")
    if not isinstance(section, dict):
        return warnings
    reports = section.get("reports")
    if reports is None:
        return warnings
    if not isinstance(reports, dict):
        warnings.append("`[colosseum.reports]` must be a table; ignored")
        return warnings
    for key, value in reports.items():
        if coerce_config_bool(value) is None:
            warnings.append(
                f"`[colosseum.reports].{key}` must be a boolean; ignored",
            )
    return warnings
