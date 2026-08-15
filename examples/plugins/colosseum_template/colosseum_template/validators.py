"""Optional config validators — register in colosseum_template/__init__.py."""

from __future__ import annotations

from typing import Any


def validate_template_device(item: dict[str, Any]) -> list[str]:
    """Return config warning strings for one ``template.device`` row.

    Register with::

        registry.register_config_validator("template.device", validate_template_device)
    """
    warnings: list[str] = []
    serial = str(item.get("serial", ""))
    if serial.upper().startswith("TEMPLATE"):
        warnings.append(
            f"template.device id={item.get('device_id')}: serial looks like a placeholder"
        )
    # TODO: Your code here — add site-specific checks.
    return warnings
