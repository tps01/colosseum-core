"""Optional per-slot parameters file (limits and command kwargs by key)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from colosseum.config.toml_relaxed import read_relaxed_toml
from colosseum.exceptions import ProceduralFault

if TYPE_CHECKING:
    from colosseum.context import RuntimeContext

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

LIMIT_FIELDS = frozenset(
    {"expected_val", "tolerance", "minimum", "maximum", "exact", "expected"},
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


def apply_parameters_to_kwargs(
    kwargs: dict[str, Any],
    *,
    key: str,
    parameters: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    """Copy omitted fields from the parameters table for ``key``.

    When a parameters file is loaded, ``key`` must exist in the file. Call
    values win over file values.
    """
    if parameters is None:
        return dict(kwargs)
    if key not in parameters:
        raise ParametersError(f"Parameters file has no section for key={key!r}")
    merged = dict(parameters[key])
    merged.update(kwargs)
    return merged


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
