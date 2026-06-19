"""Unit tests for autoconfig VISA resource sorting."""

from __future__ import annotations

from colosseum_equipment.autoconfig.sort import resource_sort_key, sort_resources


def test_tcpip_before_gpib() -> None:
    resources = [
        "GPIB0::1::INSTR",
        "TCPIP0::192.168.1.29::5025::SOCKET",
    ]
    assert sort_resources(resources) == [
        "TCPIP0::192.168.1.29::5025::SOCKET",
        "GPIB0::1::INSTR",
    ]


def test_gpib_address_ordering() -> None:
    resources = [
        "GPIB0::5::INSTR",
        "GPIB0::1::INSTR",
        "GPIB0::3::INSTR",
    ]
    assert sort_resources(resources) == [
        "GPIB0::1::INSTR",
        "GPIB0::3::INSTR",
        "GPIB0::5::INSTR",
    ]


def test_mixed_kinds_keep_global_order() -> None:
    ordered = sort_resources(
        [
            "GPIB0::2::INSTR",
            "TCPIP0::192.168.1.10::INSTR",
            "USB0::0x2A8D::0x8F01::INSTR",
            "GPIB0::1::INSTR",
        ]
    )
    assert ordered[0].startswith("TCPIP")
    assert ordered[1].startswith("USB")
    assert ordered[2:] == ["GPIB0::1::INSTR", "GPIB0::2::INSTR"]


def test_resource_sort_key_is_stable() -> None:
    resource = "TCPIP0::10.0.0.5::5025::SOCKET"
    assert resource_sort_key(resource) == resource_sort_key(resource)
