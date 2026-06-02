from __future__ import annotations

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.protocols.scpi import SCPIHelper, wait_opc
from colosseum_equipment.transports.base import Transport


class GenericVna:
    """Generic SCPI network analyzer (phase-1 sweep subset)."""

    _model = "generic"

    def __init__(self, transport: Transport, config: dict) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        self._model = str(config.get("model", "generic")).lower()

    def preset(self) -> None:
        self._scpi.write("*RST")
        wait_opc(self._scpi)

    def set_start_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"SENS:FREQ:STAR {frequency_hz:.6f}")

    def set_stop_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"SENS:FREQ:STOP {frequency_hz:.6f}")

    def set_points(self, count: int) -> None:
        self._scpi.write(f"SENS:SWE:POIN {int(count)}")

    def single_sweep(self) -> None:
        self._scpi.write("INIT:IMM")
        wait_opc(self._scpi)

    def wait_complete(self) -> None:
        wait_opc(self._scpi)

    def measure_s11_magnitude(self, trace: int = 1) -> float:
        unsupported(self._model, "measure_s11_magnitude", detail="phase-2; needs vendor driver docs")

    def close(self) -> None:
        self._scpi._transport.close()
