from __future__ import annotations

from colosseum_equipment.instruments.speca.generic import GenericSpecA
from colosseum_equipment.instruments.vsg.generic import GenericVSG
from colosseum_equipment.transports.base import Transport


def _is_generic_model(model: str) -> bool:
    return model in ("generic", "")


def build_instrument(kind: str, equipment_id: int, config: dict, transport: Transport):
    model = str(config.get("model", "generic")).lower()
    if kind == "dmm":
        if model == "keysight-edu34450a":
            from colosseum_equipment.instruments.dmm.keysight_edu34450a import KeysightEDU34450A

            return KeysightEDU34450A(transport)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.dmm.generic import GenericDMM

            return GenericDMM(transport)
    if kind == "psu":
        if model == "tdk-genesys":
            from colosseum_equipment.instruments.psu.tdk_genesys import TdkGenesysPSU

            return TdkGenesysPSU(transport, config)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.psu.generic import GenericPSU

            return GenericPSU(transport, config)
    if kind == "vsg":
        if model == "keysight-esg":
            from colosseum_equipment.instruments.vsg.keysight_esg import KeysightESGVSG

            return KeysightESGVSG(transport, config)
        if _is_generic_model(model):
            return GenericVSG(transport, config)
    if kind == "speca":
        if model == "keysight-e4407b":
            from colosseum_equipment.instruments.speca.keysight_e4407b import KeysightE4407BSpecA

            return KeysightE4407BSpecA(transport, config)
        if model == "tektronix-rsa5100b":
            from colosseum_equipment.instruments.speca.tektronix_rsa5100b import TektronixRSA5100BSpecA

            return TektronixRSA5100BSpecA(transport, config)
        if _is_generic_model(model):
            return GenericSpecA(transport, config)
    if kind == "attn":
        if model == "adaura-r3":
            from colosseum_equipment.instruments.attn.adaura_r3 import AdauraR3Attn

            return AdauraR3Attn(transport, config)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.attn.generic import GenericAttn

            return GenericAttn(transport, config)
    if kind == "pwrmeter":
        if model in ("keysight-u2001a", "keysight-u2000a", "keysight-u2000"):
            from colosseum_equipment.instruments.pwrmeter.keysight_u2000 import KeysightU2000PwrMeter

            return KeysightU2000PwrMeter(transport, config)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.pwrmeter.generic import GenericPwrMeter

            return GenericPwrMeter(transport, config)
    if kind == "rfswitch":
        if model in ("minicircuits-rc", "minicircuits-ztrc"):
            from colosseum_equipment.instruments.rfswitch.minicircuits_rc import MiniCircuitsRcSwitch

            return MiniCircuitsRcSwitch(transport, config)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.rfswitch.generic import GenericRfSwitch

            return GenericRfSwitch(transport, config)
    if kind == "oscope":
        if model == "tektronix-mdo4000":
            from colosseum_equipment.instruments.oscope.tek_mdo4000 import TekMdo4000Oscope

            return TekMdo4000Oscope(transport, config)
        if model == "tektronix-t3dso2000":
            from colosseum_equipment.instruments.oscope.tek_t3dso2000 import TekT3dso2000Oscope

            return TekT3dso2000Oscope(transport, config)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.oscope.generic import GenericOscope

            return GenericOscope(transport, config)
    if kind == "eload":
        if model == "itech-it8600":
            from colosseum_equipment.instruments.eload.itech_it8600 import ItechIT8600Eload

            return ItechIT8600Eload(transport, config)
        if model in ("chroma-8600", "chroma-8601"):
            from colosseum_equipment.instruments.eload.chroma_8600 import Chroma8600Eload

            return Chroma8600Eload(transport, config)
        if model == "agilent-6050":
            from colosseum_equipment.instruments.eload.agilent_6050 import Agilent6050Eload

            return Agilent6050Eload(transport, config)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.eload.generic import GenericEload

            return GenericEload(transport, config)
    if kind == "freqcounter":
        if model in ("keysight-53220a", "keysight-53230a"):
            from colosseum_equipment.instruments.freqcounter.keysight_53220a import Keysight53220AFreqCounter

            return Keysight53220AFreqCounter(transport, config)
        if model in ("tektronix-fca3000", "tektronix-fca3100", "tektronix-mca3000"):
            from colosseum_equipment.instruments.freqcounter.tek_fca3000 import TekFca3000FreqCounter

            return TekFca3000FreqCounter(transport, config)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.freqcounter.generic import GenericFreqCounter

            return GenericFreqCounter(transport, config)
    if kind == "vna":
        if model == "tektronix-ttr500":
            from colosseum_equipment.instruments.vna.tek_ttr500 import TekTtr500Vna

            return TekTtr500Vna(transport, config)
        if model == "rohde-znb":
            from colosseum_equipment.instruments.vna.rohde_znb import RohdeZnbVna

            return RohdeZnbVna(transport, config)
        if model == "anritsu-541xx":
            from colosseum_equipment.instruments.vna.anritsu_541xx import Anritsu541xxVna

            return Anritsu541xxVna(transport, config)
        if _is_generic_model(model):
            from colosseum_equipment.instruments.vna.generic import GenericVna

            return GenericVna(transport, config)
    if kind == "sdr":
        if _is_generic_model(model):
            from colosseum_equipment.instruments.sdr.generic import GenericSdr

            return GenericSdr(transport, config)
    raise RuntimeError(f"Unsupported equipment model `{model}` for {kind} id {equipment_id}")
