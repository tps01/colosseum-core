from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericRfSwitch(ScpiInstrumentMixin):
    _model = "generic"
    """Generic SCPI RF switch matrix (preset path names in bench config)."""

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        self._model = str(config.get("model", "generic")).lower()
        if "path" in config:
            self.set_path(str(config["path"]))

    def set_path(self, path: str) -> None:
        self._scpi.write(f"ROUT:PATH {path}")

    def set_switch(self, _switch: str, _state: int) -> None:
        unsupported(self._model, "set_switch")

    def measure_path(self) -> str:
        return self._scpi.query("ROUT:PATH?").strip()

    def preset(self) -> None:
        self._scpi.write("*RST")
