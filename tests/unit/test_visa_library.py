"""VISA transport visa_library bench key."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from colosseum_equipment.transports.visa import VISATransport


def test_resource_manager_receives_visa_library() -> None:
    rm = MagicMock()
    inst = MagicMock()
    rm.open_resource.return_value = inst
    with patch("pyvisa.ResourceManager", return_value=rm) as rm_ctor:
        VISATransport("GPIB::1::INSTR", visa_library="@ivi")

    rm_ctor.assert_called_once_with("@ivi")
    rm.open_resource.assert_called_once_with("GPIB::1::INSTR")


def test_resource_manager_default_without_visa_library() -> None:
    rm = MagicMock()
    inst = MagicMock()
    rm.open_resource.return_value = inst
    with patch("pyvisa.ResourceManager", return_value=rm) as rm_ctor:
        VISATransport("GPIB::1::INSTR")

    rm_ctor.assert_called_once_with()
