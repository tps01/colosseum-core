"""Select and apply config and metadata layers for suite slots."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from colosseum.config.loader import ConfigError, _load_toml, _resolve_load_path, apply_raw_config
from colosseum.config.metadata import _apply_metadata, _read_metadata_yaml
from colosseum.plugins.loader import ensure_plugins_loaded
from colosseum.results.reports import apply_enabled_reports

if TYPE_CHECKING:
    from pathlib import Path

    from colosseum.context import RuntimeContext
    from colosseum.runner.suite_toml import SuiteTestEntry

InputKind = Literal["config", "metadata"]
_SIBLING = {"config": "config.toml", "metadata": "metadata.yaml"}


def _is_section(value: object, dotted: str, sections: set[str]) -> bool:
    return dotted in sections or isinstance(value, dict) or (
        isinstance(value, list) and bool(value) and all(isinstance(row, dict) for row in value)
    )


def _merge_config(
    base: dict[str, Any],
    overlay: dict[str, Any],
    sections: set[str],
    prefix: str = "",
) -> dict[str, Any]:
    # Namespace children are independent sections. Direct values at a path form
    # one section. Registered tables are atomic, including their nested settings.
    namespace = f"{prefix}." if prefix else ""
    direct = any(not _is_section(value, namespace + key, sections) for key, value in overlay.items())
    merged = {
        key: value
        for key, value in base.items()
        if not direct or _is_section(value, namespace + key, sections)
    }
    for key, value in overlay.items():
        dotted = namespace + key
        previous = base.get(key)
        if dotted not in sections and isinstance(previous, dict) and isinstance(value, dict) and value:
            merged[key] = _merge_config(previous, value, sections, dotted)
        else:
            merged[key] = value
    return merged


def _read(kind: InputKind, path: Path) -> dict[str, Any]:
    resolved = _resolve_load_path(path, label=kind.capitalize())
    return _load_toml(resolved) if kind == "config" else _read_metadata_yaml(resolved)


@dataclass
class SuiteInputs:
    paths: dict[InputKind, Path | None]
    _suite: dict[InputKind, dict[str, Any]] = field(init=False)
    _test: dict[InputKind, tuple[Path, dict[str, Any]]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._suite = {kind: _read(kind, path) for kind, path in self.paths.items() if path is not None}

    def test_path(self, kind: InputKind, entry: SuiteTestEntry) -> Path | None:
        explicit = entry.config if kind == "config" else entry.metadata
        sibling = entry.path.with_name(_SIBLING[kind])
        return explicit if explicit is not None else sibling if sibling.is_file() else None

    def label_slot(self, ctx: RuntimeContext, entry: SuiteTestEntry | None) -> None:
        # The slot's logger and database read these paths before loading files.
        for kind, path in self.paths.items():
            selected = path or (self.test_path(kind, entry) if entry is not None else None)
            label = str(selected) if selected is not None else None
            if kind == "config":
                ctx.config_path = label
            else:
                ctx.metadata_path = label

    def _overlay(
        self, ctx: RuntimeContext, kind: InputKind, script: dict[str, Any],
    ) -> dict[str, Any]:
        test = self._test[kind][1] if kind in self._test else {}
        suite = self._suite.get(kind, {})
        if kind == "metadata":
            return script | test | suite
        ensure_plugins_loaded(ctx.plugin_registry)
        sections = {spec.dotted_path for spec in ctx.plugin_registry.config_section_specs()}
        sections.update(("colosseum.metadata", "colosseum.reports"))
        return _merge_config(_merge_config(script, test, sections), suite, sections)

    def attach(self, ctx: RuntimeContext, entry: SuiteTestEntry | None = None) -> None:
        self._test.clear()
        try:
            self._attach(ctx, entry)
        except (ConfigError, OSError):
            if entry is not None:
                self._test.clear()
                self._attach(ctx, None)
            raise

    def _attach(self, ctx: RuntimeContext, entry: SuiteTestEntry | None) -> None:
        for kind, suite_path in self.paths.items():
            test_path = self.test_path(kind, entry) if entry is not None else None
            if test_path is not None:
                self._test[kind] = (test_path, _read(kind, test_path))
            source = suite_path or test_path
            raw = deepcopy(self._overlay(ctx, kind, {}))
            if kind == "metadata":
                _apply_metadata(ctx, raw, str(source) if source is not None else None)
            elif source is not None:
                apply_raw_config(ctx, raw, source_label=str(source))
            else:
                ctx.config = None
                ctx.config_path = None
                ctx.config_warnings.clear()
                apply_enabled_reports(ctx)
                if ctx.db.is_initialized():
                    ctx.db.insert_run_metadata("config_path", "")
            if test_path is not None and ctx.db.is_initialized():
                ctx.db.insert_run_metadata(f"{kind}_path_test", str(test_path))

    def for_script(
        self, ctx: RuntimeContext, kind: InputKind, path: Path, raw: dict[str, Any], *, force: bool,
    ) -> tuple[dict[str, Any], str]:
        if ctx.db.is_initialized():
            ctx.db.insert_run_metadata(f"{kind}_path_script", str(path))
            ctx.db.insert_event("INFO", "config", f"{kind} script input: {path}")
        if force:
            return raw, str(path)
        test_path = self._test[kind][0] if kind in self._test else None
        source = self.paths[kind] or test_path or path
        return deepcopy(self._overlay(ctx, kind, raw)), str(source)
