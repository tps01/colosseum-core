from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from colosseum.context import RuntimeContext, apply_no_artifacts, get_context, init_context
from colosseum.logging import get_logger
from colosseum.plugins.loader import ensure_plugins_loaded

from .metadata import validate_colosseum_metadata_table
from .toml_relaxed import read_relaxed_toml

if TYPE_CHECKING:
    from .sections import ConfigSectionSpec

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

_logger = get_logger("colosseum.config")


class ConfigError(RuntimeError):
    pass


@dataclass
class ConfigStore:
    """Loaded config TOML: raw nested dict plus ID-indexed plugin sections."""

    _raw: dict[str, Any]
    _normalized: dict[str, dict[int, dict[str, Any]]]
    _specs: dict[str, ConfigSectionSpec]

    def raw(self) -> dict[str, Any]:
        return self._raw

    def get_section(self, dotted: str) -> object | None:
        cursor: object = self._raw
        for part in dotted.split("."):
            if not isinstance(cursor, dict):
                return None
            cursor = cursor.get(part)
            if cursor is None:
                return None
        return cursor

    def list_items(self, dotted: str) -> list[dict[str, Any]]:
        items = self._normalized.get(dotted, {})
        return [items[key] for key in sorted(items)]

    def get_item(self, dotted: str, item_id: int) -> dict[str, Any]:
        section = self._normalized.get(dotted)
        if section is None:
            raise ConfigError(f"Config section `{dotted}` is not registered")
        if item_id not in section:
            raise ConfigError(f"Unknown id `{item_id}` in section `{dotted}`")
        return section[item_id]

    def require_item(self, dotted: str, item_id: int) -> dict[str, Any]:
        item = self.get_item(dotted, item_id)
        spec = self._specs.get(dotted)
        if spec is None:
            return item
        missing = [key for key in spec.required_keys if key not in item or item[key] in ("", None)]
        if missing:
            raise ConfigError(
                f"Section `{dotted}` id `{item_id}` missing required keys: {', '.join(missing)}",
            )
        return item


def _get_dotted(raw: dict[str, Any], dotted: str) -> object | None:
    cursor: object = raw
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def normalize_sections(
    raw: dict[str, Any], specs: list[ConfigSectionSpec],
) -> dict[str, dict[int, dict[str, Any]]]:
    normalized: dict[str, dict[int, dict[str, Any]]] = {}
    for spec in specs:
        value = _get_dotted(raw, spec.dotted_path)
        if value is None:
            continue
        if isinstance(value, dict):
            rows = [value]
        elif isinstance(value, list):
            rows = value
        else:
            raise ValueError(f"Section `{spec.dotted_path}` must be table or array of tables")

        by_id: dict[int, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"Section `{spec.dotted_path}` contains non-table entries")
            row_id = row.get(spec.id_field)
            if row_id is None:
                raise ValueError(f"Missing id field `{spec.id_field}` in `{spec.dotted_path}`")
            if not isinstance(row_id, int):
                raise ValueError(f"ID field `{spec.id_field}` in `{spec.dotted_path}` must be int")
            if row_id in by_id:
                raise ValueError(f"Duplicate id `{row_id}` in `{spec.dotted_path}`")
            by_id[row_id] = row
        normalized[spec.dotted_path] = by_id
    return normalized


def default_test_name() -> str:
    import sys

    main_script = Path(sys.argv[0])
    if main_script.suffix == ".py" and main_script.stem:
        return main_script.stem
    return "run"


def _load_toml(config_path: Path) -> dict[str, Any]:
    try:
        return read_relaxed_toml(config_path)
    except UnicodeDecodeError as exc:
        raise ConfigError(f"Config file is not valid UTF-8: {config_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {config_path}: {exc}") from exc


def apply_raw_config(
    ctx: RuntimeContext,
    raw: dict[str, Any],
    *,
    source_label: str,
) -> ConfigStore:
    ensure_plugins_loaded(ctx.plugin_registry)
    specs = list(ctx.plugin_registry.config_section_specs())
    spec_map = {s.dotted_path: s for s in specs}
    try:
        normalized = normalize_sections(raw, specs)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    ctx.config_warnings = []
    colosseum_meta = raw.get("colosseum", {})
    if isinstance(colosseum_meta, dict):
        meta_table = colosseum_meta.get("metadata")
        if isinstance(meta_table, dict):
            ctx.config_warnings.extend(validate_colosseum_metadata_table(meta_table))
    from colosseum.results.reports import apply_enabled_reports, report_section_warnings

    ctx.config_warnings.extend(report_section_warnings(raw))
    if ctx.runtime_ready and ctx.logger is not None:
        for warning in ctx.config_warnings:
            ctx.logger.warning(warning)
    store = ConfigStore(raw, normalized, spec_map)
    ctx.config = store
    ctx.config_path = source_label
    if ctx.db.is_initialized():
        ctx.db.insert_run_metadata("config_path", source_label)
    apply_enabled_reports(ctx)
    if ctx.logger is not None:
        log_loaded_config(ctx)
    return store


def load_config(
    path: str | Path,
    *,
    no_artifacts: bool = False,
    metadata_path: str | Path | None = None,
    force: bool = False,
) -> ConfigStore:
    """Load (or replace) the TOML config store.

    When the CLI/suite already loaded ``-g``, subsequent calls without
    ``force=True`` are no-ops (warn once) so operators' ``-g`` wins over
    hardcoded script paths. Pass ``force=True`` for intentional reloads
    (for example GUI placeholder → generated TOML).
    """
    try:
        ctx = get_context()
    except RuntimeError:
        ctx = None

    if ctx is not None and ctx.session.config_pinned and not force:
        if not ctx.session.config_pin_warned:
            ctx.session.config_pin_warned = True
            message = (
                "Ignoring load_config(%s): CLI/suite -g config is pinned; "
                "pass force=True to replace"
            )
            if ctx.logger is not None:
                ctx.logger.warning(message, path)
            else:
                _logger.warning(message, path)
        if ctx.config is None:
            raise ConfigError(
                "CLI config is pinned but ConfigStore is missing; this is an internal error",
            )
        return ctx.config

    config_path = Path(path).resolve()
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    raw = _load_toml(config_path)

    if ctx is None:
        ctx = init_context(
            test_case_name=default_test_name(),
            config_path=config_path,
            metadata_path=metadata_path,
            no_artifacts=no_artifacts,
            auto_finalize=True,
        )
    else:
        apply_no_artifacts(ctx, no_artifacts=no_artifacts)
        if metadata_path is not None:
            ctx.metadata_path = str(Path(metadata_path).resolve())

    store = apply_raw_config(ctx, raw, source_label=str(config_path))
    if metadata_path is not None:
        from .metadata import load_metadata

        load_metadata(metadata_path, force=force)
    return store


def log_loaded_config(ctx: RuntimeContext) -> None:
    if ctx.config is None or ctx.logger is None:
        return
    store: ConfigStore = ctx.config
    _logger.debug("Loaded config from %s", ctx.config_path)
    for dotted_path in sorted(store._specs):
        section = store._normalized.get(dotted_path, {})
        if section:
            ids = ", ".join(str(item_id) for item_id in sorted(section))
            _logger.debug("Config section %s: %d item(s) id=[%s]", dotted_path, len(section), ids)
    if ctx.config_warnings:
        _logger.debug("Config validation produced %d warning(s)", len(ctx.config_warnings))


def get(dotted: str, default: object | None = None) -> object | None:
    try:
        ctx = get_context()
    except RuntimeError:
        if default is not None:
            return default
        raise ConfigError(
            "Configuration is not loaded. Call col.config.load_config(path).",
        ) from None
    if ctx.config is None:
        if default is not None:
            return default
        raise ConfigError("Configuration is not loaded. Call col.config.load_config(path).")
    value = ctx.config.get_section(dotted)
    if value is None:
        return default
    return value


def is_loaded() -> bool:
    try:
        ctx = get_context()
    except RuntimeError:
        return False
    return ctx.config is not None
