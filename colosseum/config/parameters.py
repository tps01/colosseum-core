"""Optional per-slot parameters file (limits and command kwargs by key)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from colosseum.config.toml_io import coerce_config_bool, read_toml
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

    Order: suite-level path (CLI ``--parameters`` or suite TOML ``parameters``),
    suite entry ``parameters``, sibling ``parameters.toml`` beside the script.
    """
    from colosseum.paths import absolute_path

    if cli_path is not None:
        return absolute_path(cli_path)
    if entry_path is not None:
        return absolute_path(entry_path)
    if script_path is not None:
        sibling = absolute_path(script_path).with_name("parameters.toml")
        if sibling.is_file():
            return sibling
    return None


def merge_parameter_tables(
    base: dict[str, dict[str, Any]],
    overlay: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return ``base`` tables with whole ``overlay`` tables replacing the same key."""
    merged = {key: dict(fields) for key, fields in base.items()}
    for key, fields in overlay.items():
        merged[key] = dict(fields)
    return merged


def load_parameters_file(path: Path) -> dict[str, dict[str, Any]]:
    """Load a parameters TOML file. Tables are keys; values are kwargs."""
    from colosseum.paths import absolute_path

    resolved = absolute_path(path)
    if not resolved.is_file():
        raise ParametersError(f"Parameters file not found: {resolved}")
    try:
        raw = read_toml(resolved)
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


def _suite_parameter_paths(
    *,
    script_path: Path | None,
    entry_path: Path | None,
    suite_path: Path | None,
    stacking: bool,
) -> list[Path]:
    """Select ordered sources for both execution and provenance."""
    test = resolve_parameters_path(script_path=script_path, entry_path=entry_path)
    if suite_path is not None and not stacking:
        return [suite_path]
    return [path for path in (test, suite_path) if path is not None]


def _attach_parameter_sources(ctx: RuntimeContext, sources: list[Path]) -> None:
    from colosseum.paths import absolute_path

    ctx.parameters_map = None
    ctx.parameters_path = None
    if not sources:
        return
    sources = [absolute_path(path) for path in sources]
    tables: dict[str, dict[str, Any]] = {}
    for path in sources:
        tables = merge_parameter_tables(tables, load_parameters_file(path))
    ctx.parameters_map = tables
    ctx.parameters_path = sources[-1]
    if ctx.db.is_initialized():
        ctx.db.insert_run_metadata("parameters_file", str(sources[-1]))
        if len(sources) > 1:
            ctx.db.insert_run_metadata("parameters_file_test", str(sources[0]))
    if ctx.logger is not None:
        ctx.logger.info("Parameters file: %s (%d section(s))", sources[-1], len(tables))
        if len(sources) > 1:
            ctx.logger.info("Parameters file (test): %s", sources[0])


def attach_parameters(ctx: RuntimeContext, path: Path | None, *, required: bool = False) -> None:
    """Attach one file, preserving optional sibling-file behavior."""
    from colosseum.paths import absolute_path

    resolved = absolute_path(path) if path is not None else None
    if resolved is not None and not required and not resolved.is_file():
        resolved = None
    _attach_parameter_sources(ctx, [resolved] if resolved is not None else [])


def attach_stacked_parameters(
    ctx: RuntimeContext,
    *,
    suite_path: Path | None,
    test_path: Path | None,
) -> None:
    """Replace whole test tables with suite tables and retain both source identities."""
    _attach_parameter_sources(ctx, [path for path in (test_path, suite_path) if path is not None])


def load_parameter(key: str, *, field: str) -> Any:  # noqa: ANN401
    """Return one field from the loaded parameters file.

    ``key`` is a TOML table name and ``field`` is a name in that table.
    A missing key returns ``None``. Values are returned exactly as tomllib
    loaded them (arrays, tables, strings, numbers, and booleans).
    """
    from colosseum.context import get_context

    ctx = get_context()
    if ctx.parameters_map is None:
        raise ParametersError("no parameters file is loaded")
    table = ctx.parameters_map.get(key)
    if table is None:
        return None
    ctx.note_parameter_use(key)
    if field not in table:
        raise ParametersError(f"parameters field {field!r} not found in [{key}]")
    return table[field]
