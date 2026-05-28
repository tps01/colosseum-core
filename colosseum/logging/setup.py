from __future__ import annotations

import logging
import platform
import sys
from datetime import datetime, timezone

from ..context import RuntimeContext


def setup_logging(ctx: RuntimeContext, *, console: bool = False) -> logging.Logger:
    logger = logging.getLogger("colosseum")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    assert ctx.output_dir is not None
    file_handler = logging.FileHandler(ctx.output_dir / "debug.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    header = [
        f"Colosseum version: {ctx.framework_version}",
        f"Python version: {sys.version}",
        f"Platform: {platform.platform()}",
        f"Test case: {ctx.test_case_name}",
        f"Suite: {ctx.suite_name or 'N/A'}",
        f"Start time: {datetime.now(timezone.utc).isoformat()}",
        f"Config file: {ctx.config_path or 'N/A'}",
        f"Output directory: {ctx.output_dir}",
    ]
    for line in header:
        logger.info(line)
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
