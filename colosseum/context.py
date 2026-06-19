from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .database import DatabaseManager
from .results.aggregation import ResultAggregator

if TYPE_CHECKING:
    from .config.loader import ConfigStore
    from .plugins.registry import PluginRegistry

_ACTIVE_CONTEXT: RuntimeContext | None = None


@dataclass
class RuntimeContext:
    config: ConfigStore | None
    output_dir: Path | None
    db: DatabaseManager
    logger: logging.Logger | None
    plugin_registry: PluginRegistry
    result_aggregator: ResultAggregator
    test_case_name: str
    suite_name: str | None
    config_path: Path | str | None
    framework_version: str
    phase: str = "test"
    finalized: bool = False
    final_exit_code: int | None = None
    debug_logging: bool = False
    resource_cache: dict[str, Any] = field(default_factory=dict)
    config_warnings: list[str] = field(default_factory=list)
    _finalized_count: int = field(default=0, repr=False)


def get_context() -> RuntimeContext | None:
    return _ACTIVE_CONTEXT


def require_context() -> RuntimeContext:
    if _ACTIVE_CONTEXT is None:
        raise RuntimeError(
            "Runtime is not initialized. Call col.config.load_config() or use `colosseum run`."
        )
    return _ACTIVE_CONTEXT


def set_context(ctx: RuntimeContext) -> RuntimeContext:
    global _ACTIVE_CONTEXT
    _ACTIVE_CONTEXT = ctx
    return ctx


def init_context(
    *,
    test_case_name: str,
    suite_name: str | None = None,
    config_path: Path | str | None = None,
) -> RuntimeContext:
    from . import __version__
    from .plugins.registry import PluginRegistry

    ctx = RuntimeContext(
        config=None,
        output_dir=None,
        db=DatabaseManager(),
        logger=None,
        plugin_registry=PluginRegistry(),
        result_aggregator=ResultAggregator(),
        test_case_name=test_case_name,
        suite_name=suite_name,
        config_path=config_path,
        framework_version=__version__,
    )
    return set_context(ctx)
