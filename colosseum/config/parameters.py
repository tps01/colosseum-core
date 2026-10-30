"""Optional per-slot parameters file (limits and command kwargs by key)."""

from __future__ import annotations

import ast
import math
from typing import TYPE_CHECKING, Any

from colosseum.config.toml_relaxed import coerce_config_bool, read_relaxed_toml
from colosseum.exceptions import ProceduralFault

if TYPE_CHECKING:
    from pathlib import Path

    from colosseum.context import RuntimeContext

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

LIMIT_FIELDS = frozenset(
    {
        "expected_val",
        "expected_result",
        "tolerance",
        "minimum",
        "maximum",
        "exact",
        "expected",
    },
)


class ParametersError(ProceduralFault):
    """Parameters file could not be loaded or applied."""


def resolve_parameters_path(
    *,
    script_path: Path | None,
    cli_path: Path | None = None,
    entry_path: Path | None = None,
) -> Path | None:
    """Return the parameters file for this slot, or ``None`` when none applies.

    Order: CLI ``--parameters``, suite entry ``parameters``, sibling
    ``parameters.toml`` beside the script.
    """
    if cli_path is not None:
        return cli_path.resolve()
    if entry_path is not None:
        return entry_path.resolve()
    if script_path is not None:
        sibling = script_path.resolve().with_name("parameters.toml")
        if sibling.is_file():
            return sibling
    return None


def load_parameters_file(path: Path) -> dict[str, dict[str, Any]]:
    """Load a parameters TOML file. Tables are keys; values are kwargs."""
    resolved = path.resolve()
    if not resolved.is_file():
        raise ParametersError(f"Parameters file not found: {resolved}")
    try:
        raw = read_relaxed_toml(resolved)
    except UnicodeDecodeError as exc:
        raise ParametersError(f"Parameters file is not valid UTF-8: {resolved}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ParametersError(f"Invalid parameters TOML: {resolved}: {exc}") from exc

    tables: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        if not isinstance(value, dict):
            raise ParametersError(
                f"Parameters section `{key}` must be a table, got {type(value).__name__}",
            )
        tables[str(key)] = dict(value)
    return tables


def is_limit_section(fields: dict[str, Any]) -> bool:
    return any(name in fields for name in LIMIT_FIELDS)


def owed_limit_keys(parameters: dict[str, dict[str, Any]]) -> list[str]:
    return [key for key, fields in parameters.items() if is_limit_section(fields)]


def coerce_bool(value: object, *, name: str = "optional") -> bool:
    """Return a bool from a real bool or a common true/false spelling.

    Strings are matched case-insensitively: ``true``, ``t``, ``yes``, ``y``,
    ``1``, and ``false``, ``f``, ``no``, ``n``, ``0``. Integers ``0`` and ``1``
    are accepted because unquoted TOML numbers load as ints.
    """
    parsed = coerce_config_bool(value)
    if parsed is None:
        raise ParametersError(f"{name} must be a boolean, got {value!r}")
    return parsed


def coerce_optional_kwarg(kwargs: dict[str, Any]) -> bool:
    """Coerce ``kwargs['optional']`` to a bool and return the decorator flag.

    Missing ``optional`` stays false and is left unset.
    """
    if "optional" not in kwargs:
        return False
    value = coerce_bool(kwargs["optional"])
    kwargs["optional"] = value
    return value


def apply_parameters_to_kwargs(
    kwargs: dict[str, Any],
    *,
    key: str,
    parameters: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    """Merge the parameters table for ``key`` over the call.

    When a parameters file is loaded and ``key`` has no section, the call kwargs
    are kept. A field present in a matching section overrides the call. A field
    only on the call is kept.
    """
    if parameters is None or key not in parameters:
        return dict(kwargs)
    merged = dict(kwargs)
    merged.update(parameters[key])
    return merged


def toml_value_supported(value: object) -> bool:
    """Return whether ``value`` can be written into an exported parameters file."""
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, str):
        return True
    if isinstance(value, list):
        return all(toml_value_supported(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and toml_value_supported(item) for key, item in value.items()
        )
    return False


_TOML_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def _escape_toml_char(char: str) -> str:
    escaped = _TOML_ESCAPES.get(char)
    if escaped is not None:
        return escaped
    code = ord(char)
    if code < 0x20 or code == 0x7F:
        return f"\\u{code:04x}"
    return char


def _toml_quoted(text: str) -> str:
    """Quote a TOML basic string, escaping controls so tomllib can reload it."""
    return '"' + "".join(_escape_toml_char(char) for char in text) + '"'


def _toml_key(name: str) -> str:
    """Format a key; bare keys are ASCII letters/digits/underscore/dash only."""
    if name and all(
        char.isascii() and (char.isalnum() or char in {"_", "-"}) for char in name
    ):
        return name
    return _toml_quoted(name)


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return _toml_quoted(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        fields = ", ".join(
            f"{_toml_key(str(key))} = {_toml_value(item)}" for key, item in value.items()
        )
        return "{ " + fields + " }"
    raise ParametersError(
        f"cannot export value of type {type(value).__name__}",
    )


def write_parameters_file(path: Path, tables: dict[str, dict[str, Any]]) -> None:
    """Write parameter sections in first-seen key order."""
    lines: list[str] = []
    for key, fields in tables.items():
        lines.append(f"[{_toml_quoted(key)}]")
        for name, value in fields.items():
            if not toml_value_supported(value):
                raise ParametersError(
                    f"key={key!r} field {name} cannot be exported ({type(value).__name__})",
                )
            lines.append(f"{_toml_key(name)} = {_toml_value(value)}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def attach_parameters(
    ctx: RuntimeContext,
    path: Path | None,
    *,
    required: bool = False,
) -> None:
    """Load parameters onto the runtime context and record the path in metadata."""
    ctx.parameters_map = None
    ctx.parameters_path = None
    if path is None:
        return
    resolved = path.resolve()
    if not resolved.is_file():
        if required:
            raise ParametersError(f"Parameters file not found: {resolved}")
        return
    ctx.parameters_map = load_parameters_file(resolved)
    ctx.parameters_path = resolved
    if ctx.db.is_initialized():
        ctx.db.insert_run_metadata("parameters_file", str(resolved))
    if ctx.logger is not None:
        ctx.logger.info("Parameters file: %s (%d section(s))", resolved, len(ctx.parameters_map))


_CONTAINER_CLOSERS = {"[": "]", "{": "}", "(": ")"}
_BARE_BOOLS = {"true": True, "yes": True, "false": False, "no": False}


def load_parameter(*, key: str, field: str) -> Any:  # noqa: ANN401
    """Return one field from the loaded parameters file.

    ``key`` is a TOML table name and ``field`` is a name in that table.
    Ints, floats, bools, and ordinary strings are returned as loaded. A string
    shaped like a list, dict, set, or tuple is parsed into that value. ``key=``
    injection still receives the TOML value stored on the context.
    """
    from colosseum.context import get_context

    ctx = get_context()
    if ctx.parameters_map is None:
        raise ParametersError("no parameters file is loaded")
    try:
        table = ctx.parameters_map[key]
    except KeyError:
        raise ParametersError(f"parameters key not found: {key}") from None
    if field not in table:
        raise ParametersError(f"parameters field {field!r} not found in [{key}]")
    try:
        return coerce_parameter_value(table[field])
    except ParametersError as exc:
        raise ParametersError(
            f"cannot parse parameters field {field!r} in [{key}]: {exc}",
        ) from exc


def coerce_parameter_value(value: object) -> object:
    """Copy ``value``, parsing collection-shaped strings into Python objects.

    Quoted numbers stay strings. A matched ``[]``, ``{}``, or ``()`` string is
    ``ast.literal_eval`` when it is a Python literal, otherwise bare words become
    strings. Bare ``true``, ``false``, ``yes``, and ``no`` become bools. A
    one-element list whose text contains whitespace stays a string.
    """
    if isinstance(value, str):
        return _coerce_parameter_string(value)
    if isinstance(value, list):
        return [coerce_parameter_value(item) for item in value]
    if isinstance(value, dict):
        return {item_key: coerce_parameter_value(item) for item_key, item in value.items()}
    return value


def _parse_error(text: str) -> ParametersError:
    return ParametersError(f"cannot parse parameter value {text!r}")


def _matched_container(text: str) -> bool:
    if len(text) < 2:
        return False
    closer = _CONTAINER_CLOSERS.get(text[0])
    return closer is not None and text[-1] == closer


def _coerce_parameter_string(raw: str) -> object:
    text = raw.strip()
    if not _matched_container(text):
        return raw
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError, TypeError):
        parsed = _parse_bare_container(text)
    if isinstance(parsed, str):
        return raw
    return parsed


def _top_level_indexes(text: str, *, separator: str, source: str) -> list[int]:
    """Return indexes of ``separator`` outside quotes and nested brackets."""
    indexes: list[int] = []
    depth = 0
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\" and (in_single or in_double):
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if in_single or in_double:
            continue
        if char in _CONTAINER_CLOSERS:
            depth += 1
            continue
        if char in _CONTAINER_CLOSERS.values():
            depth -= 1
            if depth < 0:
                raise _parse_error(source)
            continue
        if char == separator and depth == 0:
            indexes.append(index)
    if depth != 0 or in_single or in_double:
        raise _parse_error(source)
    return indexes


def _split_top_level(text: str, *, separator: str, source: str) -> list[str]:
    parts: list[str] = []
    start = 0
    for index in _top_level_indexes(text, separator=separator, source=source):
        parts.append(text[start:index])
        start = index + 1
    parts.append(text[start:])
    return parts


def _is_unquoted_prose(atom: str) -> bool:
    if atom[0] in {"'", '"', "[", "{", "("}:
        return False
    return any(char.isspace() for char in atom)


def _parse_atom(part: str, *, source: str) -> object:
    atom = part.strip()
    if not atom:
        raise _parse_error(source)
    if _matched_container(atom):
        return _coerce_parameter_string(atom)
    try:
        return ast.literal_eval(atom)
    except (SyntaxError, ValueError, TypeError):
        parsed = _BARE_BOOLS.get(atom.lower())
        if parsed is not None:
            return parsed
        return atom


def _require_hashable(value: object, *, source: str) -> None:
    try:
        hash(value)
    except TypeError as exc:
        raise _parse_error(source) from exc


def _parse_bare_set(parts: list[str], *, source: str) -> set[Any]:
    items: set[Any] = set()
    for part in parts:
        item = _parse_atom(part, source=source)
        _require_hashable(item, source=source)
        items.add(item)
    return items


def _parse_bare_dict(parts: list[str], *, source: str) -> dict[Any, Any]:
    parsed: dict[Any, Any] = {}
    for part in parts:
        colons = _top_level_indexes(part, separator=":", source=source)
        if not colons:
            raise _parse_error(source)
        split_at = colons[0]
        key = _parse_atom(part[:split_at], source=source)
        _require_hashable(key, source=source)
        parsed[key] = _parse_atom(part[split_at + 1 :], source=source)
    return parsed


def _parse_bare_container(text: str) -> object:
    opener = text[0]
    inner = text[1:-1]
    if not inner.strip():
        if opener == "[":
            return []
        if opener == "(":
            return ()
        return {}
    parts = _split_top_level(inner, separator=",", source=text)
    if parts and not parts[-1].strip():
        parts.pop()
    if not parts or any(not part.strip() for part in parts):
        raise _parse_error(text)
    if opener == "[":
        if len(parts) == 1 and _is_unquoted_prose(parts[0].strip()):
            return text
        return [_parse_atom(part, source=text) for part in parts]
    if opener == "(":
        return tuple(_parse_atom(part, source=text) for part in parts)
    if any(_top_level_indexes(part, separator=":", source=text) for part in parts):
        return _parse_bare_dict(parts, source=text)
    return _parse_bare_set(parts, source=text)
