"""Shared helpers for measurement and verification decorators."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..context import RuntimeContext, require_context


def resolve_domain(func: Callable[..., Any]) -> str:
    module = func.__module__
    if module.startswith("colosseum_shared"):
        return "shared"
    if module.startswith("colosseum_equipment"):
        return "equipment"
    if module.startswith("colosseum_host"):
        return "host"
    return getattr(func, "__colosseum_domain__", "core")


def command_id_for_module(module: str, name: str) -> str:
    if module.startswith("colosseum_equipment.io.api."):
        group = module.rsplit(".", 1)[-1]
        return f"io.{group}.{name}"
    if module.startswith("colosseum_equipment.api."):
        group = module.rsplit(".", 1)[-1]
        if not group.startswith("_"):
            return f"{group}.{name}"
    if module.startswith("colosseum_shared."):
        parts = module.split(".")
        if len(parts) >= 2:
            return f"{parts[1]}.{name}"
    if module.startswith("colosseum_host.api."):
        group = module.rsplit(".", 1)[-1]
        if not group.startswith("_"):
            return f"{group}.{name}"
    return name


def resolve_command(func: Callable[..., Any]) -> str:
    override = getattr(func, "__colosseum_command__", None)
    if override:
        return str(override)
    return command_id_for_module(func.__module__, func.__name__)


def ensure_runtime_context() -> RuntimeContext:
    return require_context()
