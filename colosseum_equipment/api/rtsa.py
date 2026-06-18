"""Real-time spectrum analyzer APIs exposed as ``col.equipment.rtsa``.

Configure instruments with ``[[equipment.rtsa]]`` in bench TOML (``rtsa_id``, ``resource``,
optional ``model`` and ``driver``; default driver is VISA/SCPI). IQ capture files are written
under the active run output directory and registered as artifacts.
"""

from __future__ import annotations

from colosseum.decorators import command

from colosseum_equipment.connections import get_cached_instrument


@command
def preset(*, rtsa_id: int) -> None:
    """Load the instrument preset (factory default state).

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).preset()


@command
def set_center_freq(*, rtsa_id: int, frequency_hz: float) -> None:
    """Set spectrum center frequency in hertz.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param frequency_hz: Center frequency in hertz.
    :type frequency_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_center_freq(frequency_hz)


@command
def set_span(*, rtsa_id: int, span_hz: float) -> None:
    """Set frequency span in hertz.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param span_hz: Frequency span in hertz.
    :type span_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_span(span_hz)


@command
def set_bandwidth(*, rtsa_id: int, bandwidth_hz: float) -> None:
    """Set resolution bandwidth in hertz.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param bandwidth_hz: Resolution bandwidth in hertz.
    :type bandwidth_hz: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_bandwidth(bandwidth_hz)


@command
def set_acq_time(*, rtsa_id: int, seconds: float) -> None:
    """Set acquisition time in seconds.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param seconds: Acquisition duration in seconds.
    :type seconds: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_acq_time(seconds)


@command
def set_continuous_run(*, rtsa_id: int, enabled: bool) -> None:
    """Enable or disable continuous acquisition.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param enabled: ``True`` for continuous run, ``False`` for single-shot.
    :type enabled: bool

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_continuous_run(enabled)


@command
def set_num_samples(*, rtsa_id: int, count: int) -> None:
    """Set the number of IQ samples to acquire.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param count: IQ sample count.
    :type count: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_num_samples(count)


@command
def get_num_samples(*, rtsa_id: int) -> int:
    """Read the configured IQ sample count.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int

    :returns: Configured IQ sample count.
    :rtype: int

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    return int(get_cached_instrument("rtsa", rtsa_id).get_num_samples())


@command
def set_trigger_source(*, rtsa_id: int, source: str) -> None:
    """Set trigger source (for example ``INPut``, ``EXTFront``, ``EXTRear``).

    Also supports ``EXTGated`` and ``LINe``.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param source: Trigger source identifier accepted by the instrument SCPI driver.
    :type source: str

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_trigger_source(source)


@command
def set_trigger_level(*, rtsa_id: int, level_dbm: float) -> None:
    """Set trigger level in dBm.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param level_dbm: Trigger level in dBm.
    :type level_dbm: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_trigger_level(level_dbm)


@command
def set_trigger_position(*, rtsa_id: int, position_dbm: float) -> None:
    """Set trigger position in dBm.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param position_dbm: Trigger position in dBm.
    :type position_dbm: float

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).set_trigger_position(position_dbm)


@command
def run(*, rtsa_id: int) -> None:
    """Start or arm a single acquisition.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).run()


@command
def save_IQ_data(*, rtsa_id: int, path: str, file_format: str = "bin") -> None:
    """Download IQ data as ``bin``, ``mat``, or ``iq.tar`` under the run directory.

    :param rtsa_id: Configured ``equipment.rtsa`` id from bench TOML.
    :type rtsa_id: int
    :param path: Relative path under the active run output directory.
    :type path: str
    :param file_format: Export format: ``bin``, ``mat``, or ``iq.tar``.
    :type file_format: str, optional

    :returns: None

    :raises EquipmentConnectionError: Transport or instrument connection failed.
    :raises EquipmentCapabilityError: Operation not supported by the configured model.
    """
    get_cached_instrument("rtsa", rtsa_id).save_IQ_data(path, file_format=file_format)
