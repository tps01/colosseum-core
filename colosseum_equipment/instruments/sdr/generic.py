from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.transports.base import Transport


class GenericSdr:
    """Placeholder SDR driver until UHD/Ettus documentation is provided."""

    _model = "generic"

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        _ = transport
        self._config = config
        self._model = str(config.get("model", "generic")).lower()

    def set_center_frequency(self, _frequency_hz: float) -> None:
        unsupported(self._model, "set_center_frequency", detail="requires UHD driver documentation")

    def set_sample_rate(self, _sample_rate: float) -> None:
        unsupported(self._model, "set_sample_rate", detail="requires UHD driver documentation")

    def set_gain(self, _gain_db: float) -> None:
        unsupported(self._model, "set_gain", detail="requires UHD driver documentation")

    def capture_iq(self, _path: str) -> None:
        unsupported(self._model, "capture_iq", detail="requires UHD driver documentation")

    def close(self) -> None:
        pass
