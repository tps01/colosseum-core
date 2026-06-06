from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from colosseum_equipment.transports.base import Transport

InstrumentBuilder = Callable[[Transport, dict[str, Any]], object]

_builders: dict[str, dict[str, InstrumentBuilder]] = defaultdict(dict)


def register(kind: str, model: str, builder: InstrumentBuilder) -> None:
    _builders[kind][model.lower()] = builder


def register_aliases(kind: str, models: tuple[str, ...], builder: InstrumentBuilder) -> None:
    for model in models:
        register(kind, model, builder)


def build_registered(kind: str, model: str, transport: Transport, config: dict[str, Any]) -> object:
    model_key = model.lower()
    kind_map = _builders.get(kind)
    if not kind_map:
        raise RuntimeError(f"Unsupported equipment kind `{kind}`")
    if model_key in kind_map:
        return kind_map[model_key](transport, config)
    if model_key in ("generic", "") and "generic" in kind_map:
        return kind_map["generic"](transport, config)
    raise RuntimeError(f"Unsupported equipment model `{model}` for {kind}")


def registered_kinds() -> frozenset[str]:
    return frozenset(_builders)
