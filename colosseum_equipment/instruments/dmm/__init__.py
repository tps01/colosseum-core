from __future__ import annotations

from colosseum_equipment.instruments.registry import register

from .generic import GenericDMM
from .keysight_edu34450a import KeysightEDU34450A


def register_instruments() -> None:
    register("dmm", "keysight-edu34450a", lambda transport, _config: KeysightEDU34450A(transport))
    register("dmm", "generic", lambda transport, _config: GenericDMM(transport))
