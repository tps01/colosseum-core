from __future__ import annotations

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.protocols.scpi import SCPIHelper, wait_opc
from colosseum_equipment.transports.base import Transport


class GenericOscope:
    """Generic SCPI oscilloscope (subset; vendor models extend)."""

    _model = "generic"

    def __init__(self, transport: Transport, config: dict) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        self._model = str(config.get("model", "generic")).lower()

    def preset(self) -> None:
        self._scpi.write("*RST")
        wait_opc(self._scpi)

    def set_timebase_scale(self, seconds_per_div: float) -> None:
        self._scpi.write(f"TIM:SCAL {seconds_per_div}")

    def single_acquire(self) -> None:
        self._scpi.write("SING")
        wait_opc(self._scpi)

    def measure_vpp(self, channel: int = 1) -> float:
        return self._scpi.query_float(f"MEAS:VPP? CH{channel}")

    def save_screenshot(self, path: str) -> None:
        unsupported(self._model, "save_screenshot")

    def close(self) -> None:
        self._scpi._transport.close()
