"""Autoconfig log emission."""

from __future__ import annotations

from colosseum.context import RuntimeContext
from colosseum.logging import get_logger

from .discovery import AutoconfigResult

_logger = get_logger("colosseum.config")


def log_autoconfig(ctx: RuntimeContext, result: AutoconfigResult) -> None:
    """Emit INFO/WARNING lines describing autoconfig assignments and skips."""
    if ctx.logger is None:
        return
    logger = ctx.logger
    logger.info("Autoconfig source: %s", ctx.config_path or "(autoconfig)")
    logger.info("Autoconfig scanned %d VISA INSTR resource(s)", result.scanned_count)
    for subnet in result.blacklist_subnets:
        logger.info(
            "Autoconfig blacklist: %s -> %s/%s (local %s)",
            subnet.interface,
            subnet.network.network_address,
            subnet.network.prefixlen,
            subnet.address,
        )
    for entry in result.unresolved_blacklist:
        logger.warning("Autoconfig blacklist entry not found: %s", entry)
    for resource, subnet in result.blacklisted:
        logger.info(
            "Autoconfig blacklisted resource=%s reason=subnet %s/%s (%s)",
            resource,
            subnet.network.network_address,
            subnet.network.prefixlen,
            subnet.interface,
        )
    for assignment in result.assignments:
        logger.info(
            "Autoconfig assigned %s id=%s resource=%s model=%s idn=%r",
            assignment.section,
            assignment.item_id,
            assignment.resource,
            assignment.model,
            assignment.idn,
        )
    for skip in result.skipped:
        logger.warning(
            "Autoconfig skipped resource=%s reason=%s%s",
            skip.resource,
            skip.reason,
            f" idn={skip.idn!r}" if skip.idn else "",
        )
    logger.info(
        "Autoconfig summary: %d assigned, %d blacklisted, %d skipped",
        len(result.assignments),
        len(result.blacklisted),
        len(result.skipped),
    )
