"""Standard TOML load helpers shared by config, suite, and parameters readers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

_TRUE_TOKENS = frozenset({"true", "t", "yes", "y", "1"})
_FALSE_TOKENS = frozenset({"false", "f", "no", "n", "0"})


def coerce_config_bool(value: object) -> bool | None:
    """Return a bool for a real bool or a common true/false spelling.

    Strings match case-insensitively: ``true``, ``t``, ``yes``, ``y``, ``1``,
    and ``false``, ``f``, ``no``, ``n``, ``0``. Integers ``0`` and ``1`` are
    accepted because unquoted TOML numbers load as ints. Anything else returns
    ``None`` so callers can keep the original value.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
    return None


def read_toml(path: Path) -> dict[str, Any]:
    """Read UTF-8 TOML from ``path`` (strips a leading BOM if present)."""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return tomllib.loads(data.decode("utf-8"))
