"""Keep the system awake for ``colosseum run`` / ``run-suite --no-sleep``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wakepy import keep

if TYPE_CHECKING:
    from collections.abc import Callable


def run_with_no_sleep(action: Callable[[], int]) -> int:
    """Run ``action`` under wakepy ``keep.running`` (sleep inhibited; screen may lock).

    :param action: Callable that performs the run and returns an exit code.
    :type action: Callable[[], int]

    :returns: Exit code from ``action`` (including coerced ``SystemExit``).
    :rtype: int
    """
    code = 0
    with keep.running():
        try:
            code = action()
        except SystemExit as exc:
            raw = exc.code
            code = raw if isinstance(raw, int) else (1 if raw else 0)
    return code
