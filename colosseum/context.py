from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .database import DatabaseManager
from .results.aggregation import ResultAggregator

_ACTIVE_CONTEXT: Optional["RuntimeContext"] = None


@dataclass
class RuntimeContext:
    config: Optional[object]
    output_dir: Optional[Path]
    db: DatabaseManager
    logger: Optional[object]
    plugin_registry: object
    result_aggregator: ResultAggregator
    test_case_name: str
    suite_name: Optional[str]
    config_path: Optional[Path]
    framework_version: str
    phase: str = "test"
    finalized: bool = False
    final_exit_code: Optional[int] = None
    verbose_logging: bool = False
    resource_cache: Dict[str, Any] = field(default_factory=dict)
    config_warnings: List[str] = field(default_factory=list)
    _finalized_count: int = field(default=0, repr=False)


def get_context() -> Optional[RuntimeContext]:
    return _ACTIVE_CONTEXT


def require_context() -> RuntimeContext:
    if _ACTIVE_CONTEXT is None:
        raise RuntimeError("Runtime is not initialized. Call col.config.load_config() or use `colosseum run`.")
    return _ACTIVE_CONTEXT


def set_context(ctx: RuntimeContext) -> RuntimeContext:
    global _ACTIVE_CONTEXT
    _ACTIVE_CONTEXT = ctx
    return ctx


def init_context(
    *,
    test_case_name: str,
    suite_name: Optional[str] = None,
    config_path: Optional[Path] = None,
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
