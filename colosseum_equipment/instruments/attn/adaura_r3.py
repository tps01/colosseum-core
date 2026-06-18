"""Adaura Technologies R3 programmable RF attenuator (text protocol).

Manual: AdauraTech Attenuator Manual R3 — ``SET [Ch] [Atten]``, ``STATUS``.
"""

from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._text_protocol import parse_adaura_status_channel
from colosseum_equipment.transports.base import Transport


class AdauraR3Attn:
    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._transport = transport
        self._channel = int(config.get("channel", 1))
        if "attenuation_db" in config:
            self.set_attenuation_db(float(config["attenuation_db"]))

    def set_attenuation_db(self, attenuation_db: float) -> None:
        self._transport.write(f"SET {self._channel} {attenuation_db:.2f}")

    def measure_attenuation_db(self) -> float:
        response = self._transport.query("STATUS")
        return parse_adaura_status_channel(response, self._channel)

    def preset(self) -> None:
        self._transport.write("RESET")

    def close(self) -> None:
        self._transport.close()
