from __future__ import annotations

from colosseum_equipment.protocols.scpi import SCPIHelper


class ScpiInstrumentMixin:
    """Mixin for SCPI instruments that close via the underlying transport."""

    _scpi: SCPIHelper

    def close(self) -> None:
        self._scpi._transport.close()
