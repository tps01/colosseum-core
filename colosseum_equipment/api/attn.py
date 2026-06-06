"""Programmable attenuator APIs (``col.equipment.attn``)."""

from __future__ import annotations

from colosseum.decorators import command, measurement

from colosseum_equipment.api._verify import tolerance_verifier
from colosseum_equipment.connections import get_cached_instrument


@command
def set_attenuation_db(*, attn_id: int, attenuation_db: float) -> None:
    """Set attenuation.

    :param attn_id: Configured ``equipment.attn`` id from bench TOML.
    :type attn_id: int
    :param attenuation_db: Attenuation in dB.
    :type attenuation_db: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("attn", attn_id).set_attenuation_db(attenuation_db)


@command
def preset(*, attn_id: int) -> None:
    """Return the instrument to a default preset.

    :param attn_id: Configured ``equipment.attn`` id from bench TOML.
    :type attn_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("attn", attn_id).preset()


@measurement
def measure_attenuation_db(*, attn_id: int, key: str) -> float:
    """Read programmed or measured attenuation.

    :param attn_id: Configured ``equipment.attn`` id from bench TOML.
    :type attn_id: int
    :param key: Unique measurement key within domain ``equipment`` and this command name.
        Must not collide with another instrument's measurement using the same command name.
    :type key: str

    :returns: Measured attenuation in dB.
    :rtype: float

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    _ = key
    return float(get_cached_instrument("attn", attn_id).measure_attenuation_db())


verify_attenuation_db = tolerance_verifier(
    "measure_attenuation_db", name="verify_attenuation_db", unit="dB"
)
