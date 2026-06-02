from __future__ import annotations

from colosseum_equipment.exceptions import EquipmentConnectionError
from colosseum_equipment.transports.base import Transport
from colosseum_equipment.transports.serial_transport import SerialTransport
from colosseum_equipment.transports.sim import SimTransport
from colosseum_equipment.transports.null_transport import NullTransport
from colosseum_equipment.transports.visa import VISATransport


def default_driver_for_kind(kind: str) -> str:
    """Default bench ``driver`` when omitted (documented by docgen config reference)."""
    if kind == "serial":
        return "serial"
    if kind == "sdr":
        return "stub"
    return "visa"


def open_transport(kind: str, equipment_id: int, config: dict) -> Transport:
    driver = str(config.get("driver", default_driver_for_kind(kind))).lower()
    timeout = float(config.get("timeout", 5.0))

    if driver == "sim":
        return SimTransport(kind, equipment_id, config)
    if driver == "visa":
        resource = config.get("resource")
        if not resource:
            raise EquipmentConnectionError(f"equipment.{kind} id {equipment_id} missing `resource`")
        visa_backend = config.get("visa_backend")
        sim_definition = config.get("sim_definition")
        visa_library = config.get("visa_library")
        return VISATransport(
            str(resource),
            timeout=timeout,
            visa_backend=str(visa_backend) if visa_backend is not None else None,
            sim_definition=str(sim_definition) if sim_definition is not None else None,
            visa_library=str(visa_library) if visa_library is not None else None,
        )
    if driver == "serial":
        port = config.get("port") or config.get("resource")
        if not port:
            raise EquipmentConnectionError(f"equipment.{kind} id {equipment_id} missing `port`")
        baudrate = int(config.get("baudrate", 115200))
        return SerialTransport(str(port), baudrate=baudrate, timeout=timeout)
    if driver in ("stub", "none"):
        return NullTransport()
    if driver == "uhd":
        raise EquipmentConnectionError(
            f"equipment.{kind} id {equipment_id}: driver `uhd` requires Ettus/UHD documentation "
            "before implementation; use driver=stub for API scaffolding."
        )
    raise EquipmentConnectionError(f"Unsupported driver `{driver}` for equipment.{kind} id {equipment_id}")
