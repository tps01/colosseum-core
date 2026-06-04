"""Colosseum equipment plugin (PSU, DMM, RF, SCPI, transports)."""

from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins.registry import PluginRegistry

from colosseum_equipment.connections import close_all, register_atexit_cleanup
from colosseum_equipment.instruments._config_keys import VISA_OPTIONAL_KEYS


_IO_CONFIG_SPECS = (
    ConfigSectionSpec(
        "io.dio",
        "dio_id",
        required_keys=(),
        optional_keys=("driver", "resource", "port_lines", "direction"),
    ),
    ConfigSectionSpec(
        "io.i2c",
        "bus_id",
        required_keys=(),
        optional_keys=("driver", "resource", "clock_hz", "address"),
    ),
    ConfigSectionSpec(
        "io.spi",
        "bus_id",
        required_keys=(),
        optional_keys=("driver", "resource", "clock_hz", "mode", "cs"),
    ),
)


def register(registry: PluginRegistry) -> None:
    from colosseum_equipment import api
    from colosseum_equipment.io import api as io_api

    registry.register_namespace("equipment", api)
    registry.register_namespace("io", io_api)
    registry.register_shutdown(close_all)
    register_atexit_cleanup()
    for spec in (*_CONFIG_SPECS, *_IO_CONFIG_SPECS):
        registry.register_config_section(spec)


def _visa_section(section: str, id_field: str, *, extra_optional: tuple[str, ...] = ()) -> ConfigSectionSpec:
    return ConfigSectionSpec(
        section,
        id_field,
        required_keys=("resource",),
        optional_keys=VISA_OPTIONAL_KEYS + extra_optional,
    )


_CONFIG_SPECS = (
    _visa_section("equipment.psu", "psu_id", extra_optional=("voltage", "ovp", "ocp")),
    _visa_section("equipment.dmm", "dmm_id"),
    ConfigSectionSpec(
        "equipment.serial",
        "serial_id",
        required_keys=("port",),
        optional_keys=("driver", "baudrate", "timeout"),
    ),
    _visa_section(
        "equipment.vsg",
        "vsg_id",
        extra_optional=("frequency", "power_dbm", "output"),
    ),
    _visa_section(
        "equipment.speca",
        "speca_id",
        extra_optional=("center_freq", "span", "rbw"),
    ),
    ConfigSectionSpec(
        "equipment.attn",
        "attn_id",
        required_keys=(),
        optional_keys=VISA_OPTIONAL_KEYS + ("attenuation_db", "channel", "port"),
    ),
    _visa_section("equipment.pwrmeter", "pwrmeter_id", extra_optional=("frequency",)),
    ConfigSectionSpec(
        "equipment.rfswitch",
        "rfswitch_id",
        required_keys=(),
        optional_keys=VISA_OPTIONAL_KEYS + ("path", "port"),
    ),
    _visa_section("equipment.oscope", "oscope_id", extra_optional=("measurement_slot",)),
    _visa_section("equipment.eload", "eload_id"),
    _visa_section("equipment.freqcounter", "freqcounter_id"),
    _visa_section("equipment.vna", "vna_id", extra_optional=("channel", "frequency_unit")),
    ConfigSectionSpec(
        "equipment.sdr",
        "sdr_id",
        required_keys=(),
        optional_keys=(
            "resource",
            "driver",
            "model",
            "interface",
            "timeout",
            "center_freq",
            "sample_rate",
            "gain_db",
        ),
    ),
)
