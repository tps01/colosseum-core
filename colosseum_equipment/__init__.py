"""Colosseum equipment plugin (PSU, DMM, SCPI, transports)."""

from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins.registry import PluginRegistry

from colosseum_equipment.connections import close_all


def register(registry: PluginRegistry) -> None:
    from colosseum_equipment import api

    registry.register_namespace("equipment", api)
    registry.register_shutdown(close_all)
    for spec in _CONFIG_SPECS:
        registry.register_config_section(spec)


_CONFIG_SPECS = (
    ConfigSectionSpec(
        "equipment.psu",
        "psu_id",
        required_keys=("driver", "resource"),
        optional_keys=("model", "interface", "voltage", "ovp", "ocp", "timeout", "visa_backend", "sim_definition"),
    ),
    ConfigSectionSpec(
        "equipment.dmm",
        "dmm_id",
        required_keys=("driver", "resource"),
        optional_keys=("model", "interface", "timeout", "visa_backend", "sim_definition"),
    ),
    ConfigSectionSpec(
        "equipment.serial",
        "serial_id",
        required_keys=("driver", "port"),
        optional_keys=("baudrate", "timeout"),
    ),
    ConfigSectionSpec(
        "equipment.vsg",
        "vsg_id",
        required_keys=("driver", "resource"),
        optional_keys=(
            "model",
            "interface",
            "frequency",
            "power_dbm",
            "output",
            "timeout",
            "visa_backend",
            "sim_definition",
        ),
    ),
    ConfigSectionSpec(
        "equipment.speca",
        "speca_id",
        required_keys=("driver", "resource"),
        optional_keys=(
            "model",
            "interface",
            "center_freq",
            "span",
            "rbw",
            "timeout",
            "visa_backend",
            "sim_definition",
        ),
    ),
)
