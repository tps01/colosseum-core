"""Unit tests for autoconfig network blacklist filtering."""

from __future__ import annotations

import ipaddress

from colosseum_equipment.autoconfig.network_filter import (
    BlockedSubnet,
    filter_resources,
    is_resource_blacklisted,
    resolve_blacklist,
)
from colosseum_host.host.collectors.network import IPv4NetworkBinding


def _bindings() -> list[IPv4NetworkBinding]:
    return [
        IPv4NetworkBinding(
            interface="eth0",
            address="10.0.0.5",
            network="10.0.0.0",
            prefix=24,
        ),
        IPv4NetworkBinding(
            interface="Ethernet 1",
            address="192.168.1.10",
            network="192.168.1.0",
            prefix=24,
        ),
    ]


def test_resolve_blacklist_by_interface_name() -> None:
    resolution = resolve_blacklist("eth0", bindings=_bindings())
    assert len(resolution.blocked) == 1
    assert resolution.blocked[0].interface == "eth0"
    assert resolution.unresolved_entries == ()


def test_resolve_blacklist_by_local_ip() -> None:
    resolution = resolve_blacklist("192.168.1.10", bindings=_bindings())
    assert len(resolution.blocked) == 1
    assert resolution.blocked[0].network == ipaddress.IPv4Network("192.168.1.0/24")


def test_unresolved_blacklist_entry() -> None:
    resolution = resolve_blacklist("missing0", bindings=_bindings())
    assert resolution.blocked == ()
    assert resolution.unresolved_entries == ("missing0",)


def test_filter_tcpip_only() -> None:
    blocked = (
        BlockedSubnet(
            interface="eth0",
            address="10.0.0.5",
            network=ipaddress.IPv4Network("10.0.0.0/24"),
            label="eth0",
        ),
    )
    resources = [
        "TCPIP0::10.0.0.42::5025::SOCKET",
        "TCPIP0::192.168.50.2::INSTR",
        "GPIB0::1::INSTR",
        "USB0::0x1234::0x5678::INSTR",
    ]
    allowed, dropped = filter_resources(resources, blocked)
    assert allowed == [
        "TCPIP0::192.168.50.2::INSTR",
        "GPIB0::1::INSTR",
        "USB0::0x1234::0x5678::INSTR",
    ]
    assert dropped == [("TCPIP0::10.0.0.42::5025::SOCKET", blocked[0])]


def test_is_resource_blacklisted_returns_subnet() -> None:
    subnet = BlockedSubnet(
        interface="eth0",
        address="10.0.0.5",
        network=ipaddress.IPv4Network("10.0.0.0/24"),
        label="eth0",
    )
    match = is_resource_blacklisted("TCPIP0::10.0.0.1::INSTR", (subnet,))
    assert match is subnet
    assert is_resource_blacklisted("GPIB0::1::INSTR", (subnet,)) is None
