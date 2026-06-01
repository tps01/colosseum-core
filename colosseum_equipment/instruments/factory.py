from __future__ import annotations

from colosseum_equipment.instruments.speca.generic import GenericSpecA
from colosseum_equipment.instruments.vsg.generic import GenericVSG
from colosseum_equipment.transports.base import Transport


def build_instrument(kind: str, equipment_id: int, config: dict, transport: Transport):
    model = str(config.get("model", "generic")).lower()
    if kind == "dmm":
        if model == "keysight-edu34450a":
            from colosseum_equipment.instruments.dmm.keysight_edu34450a import KeysightEDU34450A

            return KeysightEDU34450A(transport)
        if model in ("generic", ""):
            from colosseum_equipment.instruments.dmm.generic import GenericDMM

            return GenericDMM(transport)
    if kind == "psu":
        if model == "tdk-genesys":
            from colosseum_equipment.instruments.psu.tdk_genesys import TdkGenesysPSU

            return TdkGenesysPSU(transport, config)
        if model in ("generic", ""):
            from colosseum_equipment.instruments.psu.generic import GenericPSU

            return GenericPSU(transport, config)
    if kind == "vsg":
        if model == "keysight-esg":
            from colosseum_equipment.instruments.vsg.keysight_esg import KeysightESGVSG

            return KeysightESGVSG(transport, config)
        if model in ("generic", ""):
            return GenericVSG(transport, config)
    if kind == "speca":
        if model == "keysight-e4407b":
            from colosseum_equipment.instruments.speca.keysight_e4407b import KeysightE4407BSpecA

            return KeysightE4407BSpecA(transport, config)
        if model == "tektronix-rsa5100b":
            from colosseum_equipment.instruments.speca.tektronix_rsa5100b import TektronixRSA5100BSpecA

            return TektronixRSA5100BSpecA(transport, config)
        if model in ("generic", ""):
            return GenericSpecA(transport, config)
    raise RuntimeError(f"Unsupported equipment model `{model}` for {kind} id {equipment_id}")
