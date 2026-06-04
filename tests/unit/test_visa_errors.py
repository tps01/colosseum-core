"""Unit tests for PyVISA exception mapping."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from colosseum_equipment.exceptions import EquipmentConnectionError, EquipmentTimeoutError
from colosseum_equipment.transports.visa import VISATransport
from colosseum_equipment.transports.visa_errors import map_visa_exception


def test_map_invalid_session() -> None:
    import pyvisa

    err = map_visa_exception(pyvisa.errors.InvalidSession(), resource="GPIB::1::INSTR")
    assert isinstance(err, EquipmentConnectionError)
    assert "not open" in str(err)


def test_map_resource_locked() -> None:
    import pyvisa
    from pyvisa import constants

    exc = pyvisa.errors.VisaIOError(constants.VI_ERROR_RSRC_LOCKED)
    err = map_visa_exception(exc, resource="USB0::0x1234::INSTR")
    assert isinstance(err, EquipmentConnectionError)
    assert "locked" in str(err).lower()


def test_map_timeout() -> None:
    import pyvisa
    from pyvisa import constants

    exc = pyvisa.errors.VisaIOError(constants.VI_ERROR_TMO)
    err = map_visa_exception(exc, resource="GPIB::1::INSTR")
    assert isinstance(err, EquipmentTimeoutError)


def test_write_raises_connection_error_on_invalid_session() -> None:
    import pyvisa

    inst = MagicMock()
    inst.write.side_effect = pyvisa.errors.InvalidSession()
    rm = MagicMock()
    rm.open_resource.return_value = inst
    with patch("pyvisa.ResourceManager", return_value=rm):
        transport = VISATransport("GPIB::1::INSTR")

    with pytest.raises(EquipmentConnectionError, match="not open"):
        transport.write("*IDN?")
