"""Rohde & Schwarz ZNB vector network analyzer (SCPI).

Manual: R&S ZNB User Manual — ``SENS<n>:FREQuency:STARt/STOP``, sweep points, initiate.
"""

from __future__ import annotations

from colosseum_equipment.instruments.vna._vna_channel import init_prefix, sens_prefix
from colosseum_equipment.instruments.vna.generic import GenericVna
from colosseum_equipment.protocols.scpi import wait_opc
from colosseum_equipment.transports.base import Transport


class RohdeZnbVna(GenericVna):
    _model = "rohde-znb"

    def __init__(self, transport: Transport, config: dict) -> None:
        super().__init__(transport, config)
        self._channel = int(config.get("channel", 1))

    def set_start_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"{sens_prefix(self._channel)}:FREQ:STAR {frequency_hz:.6f}")

    def set_stop_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"{sens_prefix(self._channel)}:FREQ:STOP {frequency_hz:.6f}")

    def set_points(self, count: int) -> None:
        self._scpi.write(f"{sens_prefix(self._channel)}:SWE:POIN {int(count)}")

    def single_sweep(self) -> None:
        self._scpi.write(f"{init_prefix(self._channel)}:IMM")
        wait_opc(self._scpi)
