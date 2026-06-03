from __future__ import annotations

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.transports.base import Transport


class GenericSdr:
    """Placeholder SDR driver until UHD/Ettus documentation is provided."""

    _model = "generic"

    def __init__(self, transport: Transport, config: dict) -> None:
        _ = transport
        self._config = config
        self._model = str(config.get("model", "generic")).lower()

    def set_center_frequency(self, frequency_hz: float) -> None:
        unsupported(self._model, "set_center_frequency", detail="requires UHD driver documentation")

    def set_sample_rate(self, sample_rate: float) -> None:
        unsupported(self._model, "set_sample_rate", detail="requires UHD driver documentation")

    def set_gain(self, gain_db: float) -> None:
        unsupported(self._model, "set_gain", detail="requires UHD driver documentation")

    def capture_iq(self, path: str) -> None:
        unsupported(self._model, "capture_iq", detail="requires UHD driver documentation")

    def close(self) -> None:
        pass
