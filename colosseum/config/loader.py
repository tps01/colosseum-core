from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..context import RuntimeContext, apply_no_artifacts, get_context, init_context
from ..logging import get_logger
from ..plugins.loader import ensure_plugins_loaded
from .normalize import normalize_sections
from .sections import ConfigSectionSpec
from .toml_relaxed import read_relaxed_toml
from .validate import collect_unknown_key_warnings, run_section_validators

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

_logger = get_logger("colosseum.config")


class ConfigError(RuntimeError):
    pass


@dataclass
class ConfigStore:
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
                f"Section `{dotted}` id `{item_id}` missing required keys: {', '.join(missing)}"
            )
        return item


def _default_test_name() -> str:
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


def _apply_raw_config(
    ctx: RuntimeContext,
    raw: dict[str, Any],
    *,
    source_label: str,
) -> ConfigStore:
    """Normalize and attach a raw config dict to the active run context."""
    ensure_plugins_loaded(ctx.plugin_registry)
    specs = list(ctx.plugin_registry.config_section_specs())
    spec_map = {s.dotted_path: s for s in specs}
    try:
        normalized = normalize_sections(raw, specs)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    ctx.config_warnings = collect_unknown_key_warnings(normalized, spec_map)
    validator_map = {
        spec.dotted_path: ctx.plugin_registry.validators_for(spec.dotted_path) for spec in specs
    }
    ctx.config_warnings.extend(run_section_validators(normalized, spec_map, validator_map))
    if ctx.runtime_ready and ctx.logger is not None:
        for warning in ctx.config_warnings:
            ctx.logger.warning(warning)
    store = ConfigStore(raw, normalized, spec_map)
    ctx.config = store
    ctx.config_path = source_label
    if ctx.db.is_initialized():
        ctx.db.insert_run_metadata("config_path", source_label)
    if ctx.logger is not None:
        log_loaded_config(ctx)
    return store


def load_config(path: str | Path, *, no_artifacts: bool = False) -> ConfigStore:
    """Load and validate a bench TOML file into the active run context.

    :param path: Path to the bench configuration file.
    :type path: str | Path
    :param no_artifacts: When ``True``, skip ``outputs/``, ``debug.log``, and on-disk SQLite.
    :type no_artifacts: bool, optional

    :returns: Normalized configuration store for plugin sections.
    :rtype: ConfigStore

    :raises ConfigError: When the file is missing, invalid TOML, or fails validation.
    :raises RuntimeError: When ``no_artifacts`` is set after runtime bootstrap.
    """
    config_path = Path(path).resolve()
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    raw = _load_toml(config_path)

    existing_ctx = get_context()
    if existing_ctx is None:
        ctx = init_context(
            test_case_name=_default_test_name(),
            config_path=config_path,
            no_artifacts=no_artifacts,
        )
    else:
        ctx = existing_ctx
        apply_no_artifacts(ctx, no_artifacts=no_artifacts)

    return _apply_raw_config(ctx, raw, source_label=str(config_path))


def autoconfig(
    *,
    timeout: float = 5.0,
    visa_backend: str | None = None,
    visa_library: str | None = None,
    blacklist: str | Sequence[str] | None = None,
    export_path: str | Path | None = None,
    no_artifacts: bool = False,
) -> ConfigStore:
    """Scan VISA resources and build bench equipment config without a TOML file.

    :param timeout: Probe timeout in seconds for each VISA resource.
    :type timeout: float, optional
    :param visa_backend: Reserved for future use; VISA backend selection uses ``visa_library``.
    :type visa_backend: str | None, optional
    :param visa_library: Optional PyVISA ``ResourceManager`` library path (for example ``@ivi``).
    :type visa_library: str | None, optional
    :param blacklist: Interface name(s) or local IPv4 address(es) whose subnets are excluded
        from TCPIP autoconfig (GPIB/USB/ASRL are unaffected).
    :type blacklist: str | Sequence[str] | None, optional
    :param export_path: When set, write the generated config to this TOML file path.
    :type export_path: str | Path | None, optional
    :param no_artifacts: When ``True``, skip ``outputs/``, ``debug.log``, and on-disk SQLite.
    :type no_artifacts: bool, optional

    :returns: Normalized configuration store for discovered equipment.
    :rtype: ConfigStore

    :raises ConfigError: When PyVISA is unavailable, no resources are found, or none classify.
    :raises RuntimeError: When ``no_artifacts`` is set after runtime bootstrap.
    """
    _ = visa_backend
    from colosseum_equipment.autoconfig.discovery import discover_equipment_config
    from colosseum_equipment.autoconfig.logging import log_autoconfig

    from .toml_write import TomlWriteError, write_bench_toml

    existing_ctx = get_context()
    if existing_ctx is None:
        ctx = init_context(
            test_case_name=_default_test_name(),
            config_path="(autoconfig)",
            no_artifacts=no_artifacts,
        )
    else:
        ctx = existing_ctx
        apply_no_artifacts(ctx, no_artifacts=no_artifacts)

    result = discover_equipment_config(
        timeout=timeout,
        visa_library=visa_library,
        blacklist=blacklist,
    )
    store = _apply_raw_config(ctx, result.raw, source_label="(autoconfig)")
    if ctx.logger is not None:
        log_autoconfig(ctx, result)
    if export_path is not None:
        try:
            exported = write_bench_toml(result.raw, export_path)
        except TomlWriteError as exc:
            raise ConfigError(str(exc)) from exc
        if ctx.logger is not None:
            ctx.logger.info("Autoconfig exported config to %s", exported)
        if ctx.db.is_initialized():
            ctx.db.insert_run_metadata("config_export_path", str(exported))
    return store


def log_loaded_config(ctx: RuntimeContext) -> None:
    """Emit DEBUG summary of normalized config sections (call after logging is ready)."""
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
    """Read a top-level or nested config section from the loaded bench TOML.

    :param dotted: Dotted section path (for example ``equipment.psu``).
    :type dotted: str
    :param default: Value returned when the section is absent.
    :type default: object | None, optional

    :returns: Section value, or ``default`` when missing.
    :rtype: object | None

    :raises ConfigError: When configuration has not been loaded and ``default`` is not given.
    """
    ctx = get_context()
    if ctx is None or ctx.config is None:
        if default is not None:
            return default
        raise ConfigError("Configuration is not loaded. Call col.config.load_config(path).")
    value = ctx.config.get_section(dotted)
    if value is None:
        return default
    return value


def is_loaded() -> bool:
    """Report whether ``load_config`` has populated the active run context.

    :returns: ``True`` when a configuration store is present on the context.
    :rtype: bool
    """
    ctx = get_context()
    return ctx is not None and ctx.config is not None
