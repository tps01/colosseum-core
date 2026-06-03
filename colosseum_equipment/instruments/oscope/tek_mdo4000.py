"""Tektronix MDO4000/MSO4000B/DPO4000B oscilloscope (SCPI).

Manual: 077-0510-03 Programmer Manual — horizontal scale, measurements, acquire.
"""

from __future__ import annotations

from colosseum_equipment.instruments.oscope.generic import GenericOscope
from colosseum_equipment.protocols.scpi import wait_opc
from colosseum_equipment.transports.base import Transport


class TekMdo4000Oscope(GenericOscope):
    _model = "tektronix-mdo4000"

    def set_timebase_scale(self, seconds_per_div: float) -> None:
        self._scpi.write(f"HORizontal:SCAle {seconds_per_div}")

    def single_acquire(self) -> None:
        self._scpi.write("ACQuire:STATE RUN")
        wait_opc(self._scpi)
        self._scpi.write("ACQuire:STATE STOP")
        wait_opc(self._scpi)

    def measure_vpp(self, channel: int = 1) -> float:
        source = f"CH{channel}"
        self._scpi.write(f"MEASUrement:IMMediate:SOUrce1 {source}")
        self._scpi.write("MEASUrement:MEAS1:TYPE PK2pk")
        return self._scpi.query_float("MEASUrement:MEAS1:VALue?")

    def save_screenshot(self, path: str) -> None:
        self._scpi.write(f'SAVE:IMAGE "{path}"')
