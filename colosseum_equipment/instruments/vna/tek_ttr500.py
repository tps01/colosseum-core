"""Tektronix TTR500 series VNA (SCPI).

Manual: 077-1257-00 Programmer Manual — ``SENS<n>:FREQ:STAR/STOP``, ``SWE:POIN``, ``INIT:IMM``.
"""

from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments.vna._vna_channel import (
    calc_prefix,
    disp_prefix,
    init_prefix,
    sens_prefix,
)
from colosseum_equipment.instruments.vna.generic import GenericVna
from colosseum_equipment.protocols.scpi import wait_opc
from colosseum_equipment.transports.base import Transport


class TekTtr500Vna(GenericVna):
    _model = "tektronix-ttr500"

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        super().__init__(transport, config)
        self._channel_num = int(config.get("channel", 1))

    def _channel(self) -> int:
        return self._channel_num

    def _sens(self) -> str:
        return sens_prefix(self._channel_num)

    def _calc(self) -> str:
        return calc_prefix(self._channel_num)

    def _init(self, channel: int | None = None) -> str:
        return init_prefix(channel or self._channel_num)

    def _disp(self) -> str:
        return disp_prefix(self._channel_num)

    def set_start_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"{self._sens()}:FREQ:STAR {frequency_hz:.6f}")

    def set_stop_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"{self._sens()}:FREQ:STOP {frequency_hz:.6f}")

    def set_points(self, count: int) -> None:
        self._scpi.write(f"{self._sens()}:SWE:POIN {int(count)}")

    def single_sweep(self) -> None:
        self._scpi.write(f"{self._init()}:IMM")
        wait_opc(self._scpi)
