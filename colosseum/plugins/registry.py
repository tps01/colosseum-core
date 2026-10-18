from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from colosseum.decorators._common import stamp_evidence_domain
from colosseum.logging import get_logger

if TYPE_CHECKING:
    import types
    from pathlib import Path

    from colosseum.config.sections import ConfigSectionSpec
    from colosseum.context import RuntimeContext
    from colosseum.results.finalize import FinalizeRunResult

_logger = get_logger("colosseum.plugins")

ListenerCallback = Callable[["Path", "FinalizeRunResult", "RuntimeContext"], Any]


class PluginRegistrationError(RuntimeError):
    """Raised when plugin registration would make runtime behavior ambiguous."""


class PluginRegistry:
    def __init__(self) -> None:
        self._sections: dict[str, ConfigSectionSpec] = {}
        self._namespaces: dict[str, types.ModuleType] = {}
        self._shutdown_hooks: list[Callable[[], None]] = []
        self._listeners: dict[str, ListenerCallback] = {}
        self._loaded = False

    def register_config_section(self, spec: ConfigSectionSpec) -> None:
        if spec.dotted_path in self._sections:
            raise PluginRegistrationError(
                f"Config section `{spec.dotted_path}` is already registered.",
            )
        self._sections[spec.dotted_path] = spec

    def register_namespace(self, name: str, module: types.ModuleType) -> None:
        if name in self._namespaces:
            raise PluginRegistrationError(f"Namespace `{name}` is already registered.")
        self._namespaces[name] = module
        stamp_evidence_domain(module, name)
        _logger.debug("Registered namespace `%s`", name)

    def register_shutdown(self, hook: Callable[[], None]) -> None:
        self._shutdown_hooks.append(hook)

    def register_listener(self, name: str, callback: ListenerCallback) -> None:
        if name in self._listeners:
            raise PluginRegistrationError(f"Report listener `{name}` is already registered.")
        self._listeners[name] = callback
        _logger.debug("Registered report listener `%s`", name)

    def listener_names(self) -> list[str]:
        return list(self._listeners)

    def run_listeners(
        self,
        enabled: frozenset[str],
        output_dir: Path,
        result: FinalizeRunResult,
        ctx: RuntimeContext,
    ) -> None:
        for name in sorted(enabled):
            callback = self._listeners.get(name)
            if callback is None:
                continue
            try:
                callback(output_dir, result, ctx)
            except Exception:
                _logger.exception("Report listener `%s` failed", name)
                if ctx.logger is not None:
                    ctx.logger.exception("Report listener `%s` failed", name)

    def config_section_specs(self) -> list[ConfigSectionSpec]:
        return list(self._sections.values())

    def get_namespace(self, name: str) -> types.ModuleType:
        if name not in self._namespaces:
            raise RuntimeError(
                f"Namespace `{name}` is not registered. Install the plugin package "
                "that provides it (same environment as colosseum-core) and ensure it "
                "exposes a colosseum.plugins entry point.",
            )
        return self._namespaces[name]

    def has_namespace(self, name: str) -> bool:
        return name in self._namespaces

    def run_shutdown(self) -> None:
        for hook in reversed(self._shutdown_hooks):
            try:
                hook()
            except Exception:
                _logger.exception("Plugin shutdown hook failed")

    @property
    def loaded(self) -> bool:
        return self._loaded

    @loaded.setter
    def loaded(self, value: bool) -> None:
        self._loaded = value


def register_builtin_listeners(registry: PluginRegistry) -> None:
    """Register core WATS and JUnit listeners (opt-in via reports config/CLI)."""

    def _wats(output_dir: Path, result: FinalizeRunResult, ctx: RuntimeContext) -> None:
        from colosseum.summary.wats import write_wats_report

        write_wats_report(
            output_dir,
            ctx,
            ctx.result_aggregator,
            result.verifications,
            result.measurements,
            commands=result.commands,
        )

    def _junit(output_dir: Path, result: FinalizeRunResult, ctx: RuntimeContext) -> None:
        from colosseum.summary.junit import write_junit_report

        write_junit_report(output_dir, ctx, result)

    if "wats" not in registry.listener_names():
        registry.register_listener("wats", _wats)
    if "junit" not in registry.listener_names():
        registry.register_listener("junit", _junit)
