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
# Bare RHS spellings rewritten to TOML bool literals before parse (not quoted).
_BARE_BOOL_LITERALS = {
    token: ("true" if token.lower() in _TRUE_TOKENS else "false")
    for token in (
        "true",
        "True",
        "TRUE",
        "t",
        "T",
        "yes",
        "Yes",
        "YES",
        "y",
        "Y",
        "false",
        "False",
        "FALSE",
        "f",
        "F",
        "no",
        "No",
        "NO",
        "n",
        "N",
    )
}


def _string_state(line: str, quote: str = "") -> tuple[int, str]:
    """Locate an outside-string comment and retain only an open multiline string."""
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            if char == "\\" and quote.startswith('"'):
                index += 2
                continue
            if line.startswith(quote, index):
                index += len(quote)
                # Four/five quotes at a multiline close include one/two literal quotes.
                if len(quote) == 3:
                    for _ in range(2):
                        if index < len(line) and line[index] == quote[0]:
                            index += 1
                quote = ""
                continue
        elif char == "#":
            return index, ""
        elif char in "'\"":
            quote = char * 3 if line.startswith(char * 3, index) else char
            index += len(quote)
            continue
        index += 1
    return len(line), quote if len(quote) == 3 else ""


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
    if value in ("true", "false"):
        return False
    if value in _BARE_BOOL_LITERALS:
        return False
    return not _is_numeric_literal(value)


def prepare_toml_text(text: str) -> str:
    """Quote bare-word RHS values so ``model = keysight-e4407b`` is valid TOML.

    Bare boolean spellings (``yes``, ``True``, ``F``, …) are rewritten to TOML
    ``true`` / ``false`` literals. Quoted strings such as ``"no"`` are left alone
    so intentional string values are preserved after parse. Content inside
    multiline basic (``\"\"\"``) or literal (``'''``) strings is left unchanged.
    """
    lines: list[str] = []
    multiline = ""
    for line in text.splitlines():
        was_multiline = bool(multiline)
        comment_index, multiline = _string_state(line, multiline)
        if was_multiline or multiline:
            lines.append(line)
            continue

        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("["):
            lines.append(line)
            continue

        match = _KEY_VALUE.match(line)
        if match is None:
            lines.append(line)
            continue

        raw_value = line[match.start("value") : comment_index].strip()
        comment_suffix = f" {line[comment_index:].rstrip()}" if comment_index < len(line) else ""

        bool_literal = _BARE_BOOL_LITERALS.get(raw_value)
        if bool_literal is not None:
            lines.append(
                f"{match.group('indent')}{match.group('key')} = {bool_literal}{comment_suffix}",
            )
            continue
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


def loads_relaxed(text: str) -> dict[str, Any]:
    parsed = tomllib.loads(prepare_toml_text(text))
    if isinstance(parsed, dict):
        return parsed
    return {}


def read_relaxed_toml(path: Path) -> dict[str, Any]:
    """Read UTF-8 TOML from ``path`` with relaxed bare-word quoting (strips BOM)."""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    text = data.decode("utf-8")
    return loads_relaxed(text)
