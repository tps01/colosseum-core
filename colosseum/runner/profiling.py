"""Optional pyinstrument wrapping for ``colosseum run`` / ``run-suite --profile``."""

from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_PROFILE_HTML_NAME = "profile.html"


def require_pyinstrument() -> ModuleType:
    """Import pyinstrument or raise with an install hint.

    :returns: The ``pyinstrument`` module.
    :rtype: ModuleType

    :raises RuntimeError: When pyinstrument is not installed.
    """
    try:
        import pyinstrument
    except ImportError as exc:  # pragma: no cover - exercised via mocked import
        raise RuntimeError(
            "colosseum --profile requires pyinstrument; "
            "install with: pip install 'colosseum-core[profile]' "
            "or: pip install pyinstrument",
        ) from exc
    return cast(ModuleType, pyinstrument)


def _profile_destination() -> Path | None:
    """Return the suite container or single-run output dir when artifacts exist."""
    try:
        from colosseum.context import get_context

        ctx = get_context()
    except RuntimeError:
        return None
    if ctx.no_artifacts:
        return None
    if ctx.suite_output_dir is not None:
        return ctx.suite_output_dir
    return ctx.output_dir


def _emit_profile(profiler: Any, *, no_artifacts: bool) -> None:  # noqa: ANN401
    text = profiler.output_text(unicode=True, color=False, show_all=False)
    destination = None if no_artifacts else _profile_destination()
    if destination is None:
        print(text)
        return
    path = destination / _PROFILE_HTML_NAME
    try:
        path.write_text(profiler.output_html(), encoding="utf-8")
    except OSError as exc:
        print(text)
        print(f"Colosseum: failed to write profile HTML ({exc}); text profile above.")
        return
    print(text)
    print(f"\nProfile written to: {path}")


def run_with_profile(action: Callable[[], int], *, no_artifacts: bool) -> int:
    """Run ``action`` under pyinstrument and emit HTML or text.

    :param action: Callable that performs the run and returns an exit code.
    :type action: Callable[[], int]
    :param no_artifacts: When ``True``, print text only (no ``profile.html``).
    :type no_artifacts: bool

    :returns: Exit code from ``action`` (including coerced ``SystemExit``).
    :rtype: int
    """
    pyinstrument = require_pyinstrument()
    profiler = pyinstrument.Profiler()
    profiler.start()
    code = 0
    try:
        code = action()
    except SystemExit as exc:
        raw = exc.code
        code = raw if isinstance(raw, int) else (1 if raw else 0)
    finally:
        profiler.stop()
        _emit_profile(profiler, no_artifacts=no_artifacts)
    return code
