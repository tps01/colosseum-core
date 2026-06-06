"""Map PyVISA exceptions to Colosseum equipment errors."""

from __future__ import annotations

from typing import NoReturn

from colosseum_equipment.exceptions import (
    EquipmentConnectionError,
    EquipmentError,
    EquipmentTimeoutError,
)


def map_visa_exception(exc: BaseException, *, resource: str) -> EquipmentError:
    """Return the equipment exception to raise for a PyVISA (or wrapper) failure."""
    try:
        import pyvisa
        from pyvisa import constants
    except ImportError:  # pragma: no cover
        return EquipmentConnectionError(f"VISA error on `{resource}`: {exc}")

    if isinstance(exc, pyvisa.errors.InvalidSession):
        return EquipmentConnectionError(
            f"VISA session for `{resource}` is not open (already closed or never opened): {exc}"
        )

    if isinstance(exc, pyvisa.errors.VisaIOError):
        code = getattr(exc, "error_code", None)
        if code == constants.VI_ERROR_RSRC_LOCKED:
            return EquipmentConnectionError(
                f"VISA resource `{resource}` is locked by another session: {exc}"
            )
        if code == constants.VI_ERROR_TMO:
            return EquipmentTimeoutError(f"VISA timeout on `{resource}`: {exc}")
        message = str(exc).lower()
        if "locked" in message or "resource busy" in message:
            return EquipmentConnectionError(
                f"VISA resource `{resource}` is in use or locked: {exc}"
            )
        return EquipmentConnectionError(f"VISA I/O error on `{resource}`: {exc}")

    return EquipmentConnectionError(f"VISA error on `{resource}`: {exc}")


def raise_mapped_visa_error(exc: BaseException, *, resource: str) -> NoReturn:
    raise map_visa_exception(exc, resource=resource) from exc
