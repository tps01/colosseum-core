"""Vendor model routing and capability errors for RF instruments."""

from __future__ import annotations

import pytest

from colosseum_equipment.exceptions import EquipmentCapabilityError
from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.instruments.speca.keysight_e4407b import KeysightE4407BSpecA
from colosseum_equipment.instruments.speca.tektronix_rsa5100b import TektronixRSA5100BSpecA
from colosseum_equipment.instruments.vsg.generic import GenericVSG
from colosseum_equipment.instruments.vsg.keysight_esg import KeysightESGVSG


class _StubTransport:
    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self._responses = responses or {}
        self.written: list[str] = []
        self.raw_written: list[bytes] = []

    def write(self, data: str) -> None:
        self.written.append(data)

    def query(self, data: str) -> str:
        return self._responses.get(data.strip(), "0")

    def write_raw(self, data: bytes) -> None:
        self.raw_written.append(data)

    def read_raw(self, size: int = 655360) -> bytes:
        raw = self._responses.get("__raw__", b"#210000000000")
        if isinstance(raw, str):
            return raw.encode("ascii")
        return raw

    def close(self) -> None:
        pass


def test_keysight_vsg_model() -> None:
    transport = _StubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1"})
    inst = build_instrument("vsg", 1, {"model": "keysight-esg"}, transport)
    assert isinstance(inst, KeysightESGVSG)


def test_keysight_e4407b_speca_model() -> None:
    inst = build_instrument("speca", 1, {"model": "keysight-e4407b"}, _StubTransport())
    assert isinstance(inst, KeysightE4407BSpecA)


def test_tektronix_rsa5100b_speca_model() -> None:
    inst = build_instrument("speca", 2, {"model": "tektronix-rsa5100b"}, _StubTransport())
    assert isinstance(inst, TektronixRSA5100BSpecA)


def test_generic_vsg_upload_waveform_raises() -> None:
    inst = build_instrument("vsg", 1, {"model": "generic"}, _StubTransport())
    assert isinstance(inst, GenericVSG)
    with pytest.raises(EquipmentCapabilityError, match="upload_waveform"):
        inst.upload_waveform("local.bin", "remote.bin")


def test_e4407b_download_capture_raises() -> None:
    inst = build_instrument("speca", 1, {"model": "keysight-e4407b"}, _StubTransport())
    with pytest.raises(EquipmentCapabilityError, match="download_capture"):
        inst.download_capture("capture.bin")


def test_e4438c_upload_waveform_writes_binary(tmp_path) -> None:
    waveform = tmp_path / "iq.bin"
    waveform.write_bytes(b"deadbeef")
    transport = _StubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1", "*OPC?": "1"})
    inst = build_instrument("vsg", 1, {"model": "keysight-esg"}, transport)
    inst.upload_waveform(str(waveform), "WFM1:IQ.bin")
    assert transport.raw_written
    assert b"MMEM:DATA" in transport.raw_written[0]


def test_tek_download_capture_writes_artifact(tmp_path, unit_runtime_context) -> None:
    transport = _StubTransport(
        {
            "*IDN?": "TEKTRONIX,RSA5106B,1,1",
            "*OPC?": "1",
            "DISP:WIND:ACT:MEAS?": "SPECtrum",
            "__raw__": b"#14abcd",
        }
    )
    inst = build_instrument("speca", 2, {"model": "tektronix-rsa5100b"}, transport)
    path = inst.download_capture("captures/iq.bin", kind="iq")
    assert path.exists()
    assert path.read_bytes() == b"abcd"


def test_e4428c_upload_waveform_raises() -> None:
    transport = _StubTransport({"*IDN?": "Agilent Technologies,E4428C,1,1"})
    inst = build_instrument("vsg", 1, {"model": "keysight-esg"}, transport)
    with pytest.raises(EquipmentCapabilityError, match="E4438C"):
        inst.upload_waveform("local.bin", "remote.bin")

