"""Transport factory defaults when bench TOML omits driver."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from colosseum_equipment.transports.factory import open_transport
from colosseum_equipment.transports.sim import SimTransport


def test_open_transport_defaults_to_visa_for_psu() -> None:
    with patch("colosseum_equipment.transports.factory.VISATransport") as visa_cls:
        visa_cls.return_value = object()
        open_transport("psu", 1, {"resource": "GPIB::1::INSTR"})
    visa_cls.assert_called_once_with(
        "GPIB::1::INSTR",
        timeout=5.0,
        visa_backend=None,
        sim_definition=None,
        visa_library=None,
    )


def test_open_transport_defaults_to_serial_for_serial_kind() -> None:
    with patch("colosseum_equipment.transports.factory.SerialTransport") as serial_cls:
        serial_cls.return_value = object()
        open_transport("serial", 1, {"port": "COM4"})
    serial_cls.assert_called_once()


def test_open_transport_explicit_sim() -> None:
    with patch("colosseum_equipment.transports.factory.SimTransport", spec=SimTransport) as sim_cls:
        sim_cls.return_value = object()
        open_transport("psu", 1, {"driver": "sim", "resource": "SIM::1"})
    sim_cls.assert_called_once_with("psu", 1, {"driver": "sim", "resource": "SIM::1"})


def test_open_transport_missing_resource_raises() -> None:
    with pytest.raises(Exception, match="missing `resource`"):
        open_transport("psu", 1, {})
