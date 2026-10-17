from __future__ import annotations

import logging
import platform
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext


def _detach_handlers(logger: logging.Logger) -> None:
    """Drop handlers without closing ``sys.stdout``.

    File handlers are closed so Windows can rename the run directory. Stream
    handlers are removed only; closing them can close the process console.
    """
    for handler in list(logger.handlers):
        if isinstance(handler, logging.FileHandler):
            handler.flush()
            handler.close()
        logger.removeHandler(handler)


def _formatter() -> logging.Formatter:
    return logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")


def _output_dir_line(ctx: RuntimeContext) -> str:
    if ctx.no_artifacts:
        return "(none — no-artifacts mode)"
    if ctx.output_dir is not None:
        return str(ctx.output_dir)
    if ctx.suite_output_dir is not None:
        return str(ctx.suite_output_dir)
    # Suite kind must not be inferred from missing paths (no-artifacts clears
    # suite_output_dir). Prefer an explicit suite label over a fake no-artifacts line.
    if ctx.session.kind == "suite":
        return "(suite — container not allocated)"
    return "(none — no-artifacts mode)"


def _emit_identity_header(logger: logging.Logger, ctx: RuntimeContext) -> None:
    header = [
        f"Colosseum version: {ctx.framework_version}",
        f"Python version: {sys.version}",
        f"Platform: {platform.platform()}",
        f"Test case: {ctx.test_case_name}",
        f"Suite: {ctx.suite_name or 'N/A'}",
        f"Start time: {datetime.now(timezone.utc).isoformat()}",
        f"Config file: {ctx.config_path or 'N/A'}",
        f"Output directory: {_output_dir_line(ctx)}",
    ]
    for line in header:
        logger.info(line)


def setup_logging(
    ctx: RuntimeContext,
    *,
    console: bool = False,
    console_level: int = logging.INFO,
    file: bool = True,
) -> logging.Logger:
    """Attach Colosseum log handlers and record the run identity header.

    Call this when a run or suite slot starts. The header is written to every
    attached handler (console and/or ``debug.log``).
    """
    logger = logging.getLogger("colosseum")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    _detach_handlers(logger)

    formatter = _formatter()
    if file:
        output_dir = ctx.output_dir
        if output_dir is None:
            raise RuntimeError("file logging requires an output directory")
        file_handler = logging.FileHandler(output_dir / "debug.log", mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _emit_identity_header(logger, ctx)
    return logger


def attach_console_logger(
    ctx: RuntimeContext,
    *,
    console_level: int = logging.INFO,
) -> logging.Logger:
    """Restore a console-only logger without printing another identity header.

    Suite slots call this after finalize closes the slot ``debug.log`` so later
    suite messages still reach stdout. The next ``begin_script_slot`` call
    prints the next slot's header via ``setup_logging``.
    """
    logger = logging.getLogger("colosseum")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    _detach_handlers(logger)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(_formatter())
    logger.addHandler(console_handler)
    ctx.logger = logger
    return logger


def close_logger_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
    logger.handlers.clear()


def get_logger(name: str) -> logging.Logger:
    """Return a logger that participates in the Colosseum run log.

    ``setup_logging`` attaches handlers to the ``colosseum`` logger. Plugin and
    library code must use ``colosseum.<namespace>`` (for example
    ``colosseum.template``) or a child such as ``colosseum.template.api`` so
    records propagate into ``debug.log``. Names outside that tree never reach
    the run artifact.

    The file handler records DEBUG and above. Console output, when enabled,
    defaults to INFO.

    :param name: Logger name. Plugins use ``colosseum.<namespace>``.
    :type name: str

    :returns: Standard library logger for ``name``.
    :rtype: logging.Logger
    """
    return logging.getLogger(name)
