from __future__ import annotations

from typing import Any

from .sections import ConfigSectionSpec


def collect_unknown_key_warnings(
    normalized: dict[str, dict[int, dict]],
    specs: dict[str, ConfigSectionSpec],
) -> list[str]:
    warnings: list[str] = []
    for dotted, items in normalized.items():
        spec = specs.get(dotted)
        if spec is None:
            continue
        allowed = spec.allowed_keys()
        for item_id, row in items.items():
            for key in row:
                if key not in allowed:
                    warnings.append(
                        f"Unknown key `{key}` in config section `{dotted}` (id={item_id}); ignored at runtime"
                    )
    return warnings


def run_section_validators(
    normalized: dict[str, dict[int, dict]],
    specs: dict[str, ConfigSectionSpec],
    validators_by_section: dict[str, list],
) -> list[str]:
    messages: list[str] = []
    for dotted, fns in validators_by_section.items():
        if not fns:
            continue
        for row in normalized.get(dotted, {}).values():
            for fn in fns:
                messages.extend(fn(row))
    return messages
