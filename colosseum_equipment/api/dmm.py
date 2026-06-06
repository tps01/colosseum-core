"""Digital multimeter APIs (``col.equipment.dmm``)."""

from __future__ import annotations

from colosseum.decorators import measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@measurement
def measure_voltage(*, dmm_id: int, channel: int, key: str) -> float:
    """Measure DC voltage on a channel.

    :param dmm_id: Configured ``equipment.dmm`` id from bench TOML.
    :type dmm_id: int
    :param channel: Front-panel or scanner channel index (model-specific).
    :type channel: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured voltage in volts.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    instrument = get_cached_instrument("dmm", dmm_id)
    return float(instrument.measure_voltage(channel))


verify_voltage = tolerance_verifier("measure_voltage", name="verify_voltage", unit="V")


@measurement
def measure_current(*, dmm_id: int, channel: int, key: str) -> float:
    """Measure DC current on a channel.

    :param dmm_id: Configured ``equipment.dmm`` id from bench TOML.
    :type dmm_id: int
    :param channel: Front-panel or scanner channel index (model-specific).
    :type channel: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured current in amperes.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("dmm", dmm_id).measure_current(channel))


verify_current = tolerance_verifier("measure_current", name="verify_current", unit="A")


@measurement
def measure_resistance(*, dmm_id: int, channel: int, key: str) -> float:
    """Measure resistance on a channel.

    :param dmm_id: Configured ``equipment.dmm`` id from bench TOML.
    :type dmm_id: int
    :param channel: Front-panel or scanner channel index (model-specific).
    :type channel: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured resistance in ohms.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("dmm", dmm_id).measure_resistance(channel))


verify_resistance = tolerance_verifier("measure_resistance", name="verify_resistance", unit="ohm")
