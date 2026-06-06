"""VSG SCPI delegation, waveform upload transport selection, and sweep helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from colosseum_equipment.exceptions import EquipmentCapabilityError
from colosseum_equipment.instruments.factory import build_instrument
from colosseum_equipment.instruments.vsg.generic import GenericVSG
from colosseum_equipment.instruments.vsg.keysight_esg import KeysightESGVSG

from tests.support.stubs import RfStubTransport


def test_generic_vsg_new_methods_raise() -> None:
    inst = build_instrument("vsg", 1, {"model": "generic"}, RfStubTransport())
    assert isinstance(inst, GenericVSG)
    with pytest.raises(EquipmentCapabilityError, match="delete_waveform"):
        inst.delete_waveform("WFM1:test.bin")
    with pytest.raises(EquipmentCapabilityError, match="play_iq"):
        inst.play_iq("WFM1:test.bin", 1e9, -10.0, 100e6)


def test_keysight_vsg_control_commands_write_scpi() -> None:
    transport = RfStubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1", "*OPC?": "1"})
    inst = build_instrument("vsg", 1, {"model": "keysight-esg"}, transport)
    assert isinstance(inst, KeysightESGVSG)

    inst.pulse_source("PULSE")
    inst.pulse_source("EXT2")
    inst.toggle_multitone(True)
    inst.delete_waveform("WFM1:IQ.bin")
    inst.delete_all_waveforms()
    inst.set_multicarrier(4, 1e6)
    inst.freq_sweep(1e9, 2e9, 11, 0.5)
    inst.step_power(-20.0, -10.0, 2.0, 0.25)
    inst.set_pulse_period(0.001)
    inst.set_pulse_width(0.0001)

    assert transport.written == [
        "PULM:SOUR INT",
        "PULM:INT:FUNC SHAP PULS",
        "PULM:SOUR EXT2",
        "RAD:MTONe:ARB:STAT 1",
        'MMEM:DEL "WFM1:IQ.bin"',
        "MMEM:DEL:WFM1",
        "RAD:DMOD:ARB:SETup:MCARrier:TABLe INIT,CUSTom,4,1000000.000000",
        "LIST:TYPE STEP",
        "FREQ:STAR 1000000000.000000",
        "FREQ:STOP 2000000000.000000",
        "SWE:POIN 11",
        "SWE:DWEL 0.500000000",
        "INIT:CONT ON",
        "LIST:TYPE STEP",
        "POW:STAR -20.000",
        "POW:STOP -10.000",
        "SWE:POIN 6",
        "SWE:DWEL 0.250000000",
        "LIST:TRIG:SOUR IMM",
        "INIT:CONT ON",
        "PULM:INT:PER 0.001000000",
        "PULM:INT:PWID 0.000100000",
    ]


def test_play_iq_writes_composite_scpi() -> None:
    transport = RfStubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1"})
    inst = build_instrument("vsg", 1, {"model": "keysight-esg"}, transport)
    inst.play_iq("WFM1:IQ.bin", 1.5e9, -12.0, 100e6)
    assert transport.written == [
        'RAD:ARB:WAV "WFM1:IQ.bin"',
        "FREQ:CW 1500000000.000000",
        "POW:AMPL -12.000",
        "RAD:ARB:SCLock:RATE 100000000.000000",
        "RAD:ARB:STAT 1",
        "OUTP:MOD ON",
    ]


def test_upload_waveform_tcp_binary_block(tmp_path) -> None:
    waveform = tmp_path / "iq.bin"
    waveform.write_bytes(b"\x00\x01\x02\x03" * 4)
    transport = RfStubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1", "*OPC?": "1"})
    config = {
        "model": "keysight-esg",
        "resource": "TCPIP0::192.168.0.10::inst0::INSTR",
    }
    inst = build_instrument("vsg", 1, config, transport)
    inst.upload_waveform(str(waveform), "WFM1:IQ.bin")
    assert transport.raw_written
    assert b'MMEM:DATA "WFM1:IQ.bin" ' in transport.raw_written[0]


def test_upload_waveform_ftp_fallback(tmp_path) -> None:
    waveform = tmp_path / "iq.bin"
    waveform.write_bytes(b"\x00\x01\x02\x03" * 4)
    transport = RfStubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1", "*OPC?": "1"})
    config = {
        "model": "keysight-esg",
        "resource": "GPIB::19::INSTR",
        "ftp_host": "10.0.0.5",
    }
    inst = build_instrument("vsg", 1, config, transport)

    mock_ftp = MagicMock()
    mock_ftp.__enter__.return_value = mock_ftp
    with (
        patch(
            "colosseum_equipment.instruments.vsg.waveform_upload._supports_scpi_binary_upload",
            return_value=False,
        ),
        patch("colosseum_equipment.instruments.vsg.waveform_upload.ftplib.FTP", return_value=mock_ftp),
    ):
        inst.upload_waveform(str(waveform), "WFM1:IQ.bin")

    mock_ftp.login.assert_called_once_with(user="anonymous", passwd="")
    mock_ftp.storbinary.assert_called_once()
    assert mock_ftp.storbinary.call_args.args[0] == "STOR /USER/BBG1/WAVEFORM/IQ.bin"


def test_upload_waveform_first_last_blanking(tmp_path) -> None:
    waveform = tmp_path / "iq.bin"
    waveform.write_bytes(b"\x00\x01\x02\x03" * 5)
    transport = RfStubTransport({"*IDN?": "Agilent Technologies,E4438C,1,1", "*OPC?": "1"})
    config = {
        "model": "keysight-esg",
        "resource": "TCPIP0::192.168.0.10::inst0::INSTR",
    }
    inst = build_instrument("vsg", 1, config, transport)
    inst.upload_waveform(str(waveform), "WFM1:IQ.bin", first_last_blanking=True)
    assert 'RAD:ARB:MARK:CLEAR:ALL "WFM1:IQ.bin",1' in transport.written
    assert 'RAD:ARB:MARK:SET "WFM1:IQ.bin",1,1,1,1,0' in transport.written
    assert 'RAD:ARB:MARK:SET "WFM1:IQ.bin",1,5,1,1,0' in transport.written
    assert "RAD:ARB:MDEStination:PULSe M1" in transport.written
