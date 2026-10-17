"""Explicit run session state (suite vs single, abort, modes).

Suite pass/fail and fail-fast stop metadata live here so they survive per-slot
aggregator resets and early ``endex()`` that closes the slot database.

Logging helpers own the header contract: ``start_logging`` emits the identity
header once per slot/session start; ``reattach_console`` restores stdout
without reprinting it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from colosseum.runner.run_options import ExecutionMode

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext

RunKind = Literal["single", "suite"]


@dataclass
class RunSession:
    kind: RunKind = "single"
    suite_failed: bool = False
    suite_fail_reason: str | None = None
    fail_fast_stopped: bool = False
    fail_fast_stop_reason: str | None = None
    fail_fast_stop_script: str | None = None
    requested_execution_mode: ExecutionMode = "full"
    # CLI -g / -m pins: later script loads are no-ops unless force=True.
    config_pinned: bool = False
    config_pin_warned: bool = False
    metadata_pinned: bool = False
    metadata_pin_warned: bool = False

    def mark_suite_failed(self, reason: str) -> None:
        self.suite_failed = True
        if self.suite_fail_reason is None:
            self.suite_fail_reason = reason

    def mark_fail_fast_stopped(self, script: Path, reason: str) -> None:
        self.fail_fast_stopped = True
        self.fail_fast_stop_reason = reason
        self.fail_fast_stop_script = str(script)
        self.mark_suite_failed(f"fail_fast:{reason}:{script}")

    def start_logging(
        self,
        ctx: RuntimeContext,
        *,
        console: bool = False,
        console_level: int = logging.INFO,
        file: bool = True,
    ) -> logging.Logger:
        """Begin logging for a run or slot (emits identity header)."""
        from colosseum.logging.setup import setup_logging

        return setup_logging(
            ctx, console=console, console_level=console_level, file=file,
        )

    def reattach_console(
        self,
        ctx: RuntimeContext,
        *,
        console_level: int = logging.INFO,
    ) -> logging.Logger:
        """Restore console logging after slot finalize without a new header."""
        from colosseum.logging.setup import attach_console_logger

        return attach_console_logger(ctx, console_level=console_level)
