"""Vendor model routing and capability errors for RF instruments."""

from __future__ import annotations

from pathlib import Path

import pytest
from colosseum.context import RuntimeContext
from colosseum_equipment.exceptions import EquipmentCapabilityError
from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.instruments.rtsa.tektronix_rsa5100b import TektronixRSA5100BRtsa
from colosseum_equipment.instruments.speca.keysight_e4407b import KeysightE4407BSpecA
from colosseum_equipment.instruments.vna.anritsu_541xx import Anritsu541xxVna
from colosseum_equipment.instruments.vsg.generic import GenericVSG
from colosseum_equipment.instruments.vsg.keysight_esg import KeysightESGVSG
from tests.support.stubs import RfStubTransport


def test_keysight_vsg_model() -> None:
    transport = RfStubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1"})
    inst = build_instrument("vsg", 1, {"model": "keysight-esg"}, transport)
    assert isinstance(inst, KeysightESGVSG)


def test_keysight_e4407b_speca_model() -> None:
    inst = build_instrument("speca", 1, {"model": "keysight-e4407b"}, RfStubTransport())
    assert isinstance(inst, KeysightE4407BSpecA)


def test_vna_alias_model_routes() -> None:
    inst = build_instrument("vna", 1, {"model": "anritsu-541xx"}, RfStubTransport())
    assert isinstance(inst, Anritsu541xxVna)


def test_tektronix_rsa5100b_rtsa_model() -> None:
    inst = build_instrument("rtsa", 1, {"model": "tektronix-rsa5100b"}, RfStubTransport())
    assert isinstance(inst, TektronixRSA5100BRtsa)


def test_generic_vsg_upload_waveform_raises() -> None:
    inst = build_instrument("vsg", 1, {"model": "generic"}, RfStubTransport())
    assert isinstance(inst, GenericVSG)
    with pytest.raises(EquipmentCapabilityError, match="upload_waveform"):
        inst.upload_waveform("local.bin", "remote.bin")


def test_e4438c_upload_waveform_writes_binary(tmp_path: Path) -> None:
    waveform = tmp_path / "iq.bin"
    waveform.write_bytes(b"deadbeef")
    transport = RfStubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1", "*OPC?": "1"})
    inst = build_instrument("vsg", 1, {"model": "keysight-esg"}, transport)
    inst.upload_waveform(str(waveform), "WFM1:IQ.bin")
    assert transport.raw_written
    assert b"MMEM:DATA" in transport.raw_written[0]


def test_tek_save_iq_data_writes_artifact(unit_runtime_context: RuntimeContext) -> None:
    _ = unit_runtime_context
    transport = RfStubTransport(
        {
            "*IDN?": "TEKTRONIX,RSA5106B,1,1",
            "*OPC?": "1",
            "DISP:WIND:ACT:MEAS?": "SPECtrum",
            "DISP:SPEC:FREQ:OFFS?": "1000000000.0",
            "DISP:SPEC:FREQ:SCAL?": "10000000.0",
            "SENS:SPEC:ACQ:POIN?": "1024",
            "__raw__": b"#14abcd",
        }
    )
    inst = build_instrument("rtsa", 1, {"model": "tektronix-rsa5100b"}, transport)
    path = inst.save_IQ_data("captures/iq.bin", file_format="bin")
    assert path.exists()
    assert path.read_bytes() == b"abcd"


def test_e4428c_upload_waveform_raises() -> None:
    transport = RfStubTransport({"*IDN?": "Agilent Technologies,E4428C,1,1"})
    inst = build_instrument("vsg", 1, {"model": "keysight-esg"}, transport)
    with pytest.raises(EquipmentCapabilityError, match="E4438C"):
        inst.upload_waveform("local.bin", "remote.bin")
