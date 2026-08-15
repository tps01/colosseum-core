"""VISA autoconfig entry point for ``col.equipment.autoconfig``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from colosseum.config.loader import (
    ConfigError,
    ConfigStore,
    apply_raw_config,
    default_test_name,
)
from colosseum.config.toml_write import TomlWriteError, write_bench_toml
from colosseum.context import apply_no_artifacts, get_context, init_context

from colosseum_equipment.autoconfig.discovery import discover_equipment_config
from colosseum_equipment.autoconfig.logging import log_autoconfig


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

    existing_ctx = get_context()
    if existing_ctx is None:
        ctx = init_context(
            test_case_name=default_test_name(),
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
    store = apply_raw_config(ctx, result.raw, source_label="(autoconfig)")
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
