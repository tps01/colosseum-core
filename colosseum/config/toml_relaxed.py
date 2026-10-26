"""Relax config/suite TOML: bare words on the RHS of ``key = value`` become strings."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

_KEY_VALUE = re.compile(r"^(?P<indent>\s*)(?P<key>[\w.-]+)\s*=\s*(?P<value>.+?)\s*$")
_TRUE_TOKENS = frozenset({"true", "t", "yes", "y", "1"})
_FALSE_TOKENS = frozenset({"false", "f", "no", "n", "0"})


def _split_inline_comment(value_part: str) -> tuple[str, str]:
    in_single = False
    in_double = False
    for index, char in enumerate(value_part):
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single
        elif char == "#" and not in_single and not in_double:
            value = value_part[:index].rstrip()
            comment = value_part[index:].rstrip()
            return value, f" {comment}" if comment else ""
    return value_part.strip(), ""


def _is_numeric_literal(value: str) -> bool:
    try:
        if value.startswith(("0x", "0o", "0b")):
            int(value, 0)
            return True
        if any(ch in value for ch in (".", "e", "E")):
            float(value)
            return True
        int(value)
        return True
    except ValueError:
        return False


def _needs_quoting(value: str) -> bool:
    if not value:
        return False
    if value[0] in "\"'[{:":
        return False
    # Only the lowercase TOML literals parse as bools. ``True`` and ``T`` are
    # quoted here and turned into bools after the file loads.
    if value in ("true", "false"):
        return False
    return not _is_numeric_literal(value)


def prepare_toml_text(text: str) -> str:
    """Quote bare-word RHS values so ``model = keysight-e4407b`` is valid TOML."""
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("["):
            lines.append(line)
            continue

        match = _KEY_VALUE.match(line)
        if match is None:
            lines.append(line)
            continue

        raw_value, comment_suffix = _split_inline_comment(match.group("value"))
        if not _needs_quoting(raw_value):
            lines.append(line)
            continue

        escaped = raw_value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{match.group("indent")}{match.group("key")} = "{escaped}"{comment_suffix}')
    if text.endswith("\n"):
        return "\n".join(lines) + "\n"
    return "\n".join(lines)


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


def _coerce_bool_strings(value: object) -> object:
    """Turn boolean spellings into bools. Integers stay integers."""
    if isinstance(value, dict):
        return {key: _coerce_bool_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_coerce_bool_strings(item) for item in value]
    if isinstance(value, str):
        coerced = coerce_config_bool(value)
        if coerced is not None:
            return coerced
    return value


def loads_relaxed(text: str) -> dict[str, Any]:
    parsed = tomllib.loads(prepare_toml_text(text))
    coerced = _coerce_bool_strings(parsed)
    if isinstance(coerced, dict):
        return coerced
    return parsed


def read_relaxed_toml(path: Path) -> dict[str, Any]:
    """Read UTF-8 TOML from ``path`` with relaxed bare-word quoting (strips BOM)."""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    text = data.decode("utf-8")
    return loads_relaxed(text)
