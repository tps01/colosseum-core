from __future__ import annotations

from typing import Optional

from colosseum_equipment.connections import get_transport
from colosseum_equipment.protocols.scpi import SCPIHelper

_KIND_ID_PARAMS: dict[str, str] = {
    "psu_id": "psu",
    "dmm_id": "dmm",
    "serial_id": "serial",
    "vsg_id": "vsg",
    "speca_id": "speca",
    "attn_id": "attn",
    "pwrmeter_id": "pwrmeter",
    "rfswitch_id": "rfswitch",
    "oscope_id": "oscope",
    "eload_id": "eload",
    "freqcounter_id": "freqcounter",
    "vna_id": "vna",
    "sdr_id": "sdr",
}


def for_instrument(kind: str, equipment_id: int) -> SCPIHelper:
    return SCPIHelper(get_transport(kind, equipment_id))


def _resolve_kind(**kwargs: object) -> tuple[str, int]:
    selected = [
        (kwargs[param], kind)
        for param, kind in _KIND_ID_PARAMS.items()
        if kwargs.get(param) is not None
    ]
    if len(selected) != 1:
        names = ", ".join(f"{name}=" for name in _KIND_ID_PARAMS)
        raise ValueError(f"Specify exactly one of {names}")
    value, kind = selected[0]
    return kind, int(value)  # type: ignore[arg-type]


def write(
    *,
    command: str,
    psu_id: Optional[int] = None,
    dmm_id: Optional[int] = None,
    serial_id: Optional[int] = None,
    vsg_id: Optional[int] = None,
    speca_id: Optional[int] = None,
    attn_id: Optional[int] = None,
    pwrmeter_id: Optional[int] = None,
    rfswitch_id: Optional[int] = None,
    oscope_id: Optional[int] = None,
    eload_id: Optional[int] = None,
    freqcounter_id: Optional[int] = None,
    vna_id: Optional[int] = None,
    sdr_id: Optional[int] = None,
) -> None:
    kind, equipment_id = _resolve_kind(
        psu_id=psu_id,
        dmm_id=dmm_id,
        serial_id=serial_id,
        vsg_id=vsg_id,
        speca_id=speca_id,
        attn_id=attn_id,
        pwrmeter_id=pwrmeter_id,
        rfswitch_id=rfswitch_id,
        oscope_id=oscope_id,
        eload_id=eload_id,
        freqcounter_id=freqcounter_id,
        vna_id=vna_id,
        sdr_id=sdr_id,
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
    attn_id: Optional[int] = None,
    pwrmeter_id: Optional[int] = None,
    rfswitch_id: Optional[int] = None,
    oscope_id: Optional[int] = None,
    eload_id: Optional[int] = None,
    freqcounter_id: Optional[int] = None,
    vna_id: Optional[int] = None,
    sdr_id: Optional[int] = None,
) -> str:
    kind, equipment_id = _resolve_kind(
        psu_id=psu_id,
        dmm_id=dmm_id,
        serial_id=serial_id,
        vsg_id=vsg_id,
        speca_id=speca_id,
        attn_id=attn_id,
        pwrmeter_id=pwrmeter_id,
        rfswitch_id=rfswitch_id,
        oscope_id=oscope_id,
        eload_id=eload_id,
        freqcounter_id=freqcounter_id,
        vna_id=vna_id,
        sdr_id=sdr_id,
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
    attn_id: Optional[int] = None,
    pwrmeter_id: Optional[int] = None,
    rfswitch_id: Optional[int] = None,
    oscope_id: Optional[int] = None,
    eload_id: Optional[int] = None,
    freqcounter_id: Optional[int] = None,
    vna_id: Optional[int] = None,
    sdr_id: Optional[int] = None,
) -> float:
    kind, equipment_id = _resolve_kind(
        psu_id=psu_id,
        dmm_id=dmm_id,
        serial_id=serial_id,
        vsg_id=vsg_id,
        speca_id=speca_id,
        attn_id=attn_id,
        pwrmeter_id=pwrmeter_id,
        rfswitch_id=rfswitch_id,
        oscope_id=oscope_id,
        eload_id=eload_id,
        freqcounter_id=freqcounter_id,
        vna_id=vna_id,
        sdr_id=sdr_id,
    )
    return for_instrument(kind, equipment_id).query_float(command)
