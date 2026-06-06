from __future__ import annotations

from typing import NoReturn

from colosseum_equipment.exceptions import EquipmentCapabilityError


def unsupported(model: str, operation: str, *, detail: str = "") -> NoReturn:
    message = f"{operation} is not supported by model `{model}`"
    if detail:
        message = f"{message} ({detail})"
    raise EquipmentCapabilityError(message)
