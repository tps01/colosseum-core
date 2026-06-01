from __future__ import annotations

from typing import Optional

from colosseum_equipment.connections import get_transport
from colosseum_equipment.protocols.scpi import SCPIHelper


def for_instrument(kind: str, equipment_id: int) -> SCPIHelper:
    return SCPIHelper(get_transport(kind, equipment_id))


def _resolve_kind(
    *,
    psu_id: Optional[int] = None,
    dmm_id: Optional[int] = None,
    serial_id: Optional[int] = None,
    vsg_id: Optional[int] = None,
    speca_id: Optional[int] = None,
) -> tuple[str, int]:
    ids = [
        (psu_id, "psu"),
        (dmm_id, "dmm"),
        (serial_id, "serial"),
        (vsg_id, "vsg"),
        (speca_id, "speca"),
    ]
    selected = [(value, kind) for value, kind in ids if value is not None]
    if len(selected) != 1:
        raise ValueError(
            "Specify exactly one of psu_id=, dmm_id=, serial_id=, vsg_id=, or speca_id="
        )
    return selected[0][1], int(selected[0][0])


def write(
    *,
    command: str,
    psu_id: Optional[int] = None,
    dmm_id: Optional[int] = None,
    serial_id: Optional[int] = None,
    vsg_id: Optional[int] = None,
    speca_id: Optional[int] = None,
) -> None:
    kind, equipment_id = _resolve_kind(
        psu_id=psu_id,
        dmm_id=dmm_id,
        serial_id=serial_id,
        vsg_id=vsg_id,
        speca_id=speca_id,
    )
    for_instrument(kind, equipment_id).write(command)


def query(
    *,
    command: str,
    psu_id: Optional[int] = None,
    dmm_id: Optional[int] = None,
    serial_id: Optional[int] = None,
    vsg_id: Optional[int] = None,
    speca_id: Optional[int] = None,
) -> str:
    kind, equipment_id = _resolve_kind(
        psu_id=psu_id,
        dmm_id=dmm_id,
        serial_id=serial_id,
        vsg_id=vsg_id,
        speca_id=speca_id,
    )
    return for_instrument(kind, equipment_id).query(command)


def query_float(
    *,
    command: str,
    psu_id: Optional[int] = None,
    dmm_id: Optional[int] = None,
    serial_id: Optional[int] = None,
    vsg_id: Optional[int] = None,
    speca_id: Optional[int] = None,
) -> float:
    kind, equipment_id = _resolve_kind(
        psu_id=psu_id,
        dmm_id=dmm_id,
        serial_id=serial_id,
        vsg_id=vsg_id,
        speca_id=speca_id,
    )
    return for_instrument(kind, equipment_id).query_float(command)
