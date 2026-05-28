from __future__ import annotations

from colosseum_equipment.instruments.dmm.generic import GenericDMM
from colosseum_equipment.instruments.psu.generic import GenericPSU
from colosseum_equipment.transports.base import Transport


def build_instrument(kind: str, equipment_id: int, config: dict, transport: Transport):
    model = str(config.get("model", "generic")).lower()
    if kind == "dmm":
        if model == "keysight-edu34450a":
            from colosseum_equipment.instruments.dmm.keysight_edu34450a import KeysightEDU34450A

            return KeysightEDU34450A(transport)
        if model in ("generic", ""):
            return GenericDMM(transport)
    if kind == "psu":
        if model == "tdk-genesys":
            from colosseum_equipment.instruments.psu.tdk_genesys import TdkGenesysPSU

            return TdkGenesysPSU(transport, config)
        if model in ("generic", ""):
            return GenericPSU(transport, config)
    raise RuntimeError(f"Unsupported equipment model `{model}` for {kind} id {equipment_id}")
