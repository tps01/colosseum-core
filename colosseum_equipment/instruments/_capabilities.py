from __future__ import annotations

from colosseum_equipment.exceptions import EquipmentCapabilityError


def unsupported(model: str, operation: str, *, detail: str = "") -> None:
    message = f"{operation} is not supported by model `{model}`"
    if detail:
        message = f"{message} ({detail})"
    raise EquipmentCapabilityError(message)
