"""Colosseum extension template — register() wires namespace and config."""

from colosseum.config.sections import ConfigSectionSpec
from colosseum.logging import get_logger
from colosseum.plugins.registry import PluginRegistry

_logger = get_logger("colosseum.template")


def register(registry: PluginRegistry) -> None:
    from colosseum_template import api

    # Required: expose public API as col.template.* (TODO: rename namespace when forking).
    registry.register_namespace("template", api)
    _logger.debug("Registered col.template namespace")

    # Required: declare repeatable bench TOML section(s).
    registry.register_config_section(
        ConfigSectionSpec(
            "template.device",
            "device_id",
            required_keys=("serial",),
            optional_keys=("label",),
        )
    )

    # TODO: Optional custom validation (uncomment after implementing validators.py).
    # from colosseum_template.validators import validate_template_device
    # registry.register_config_validator("template.device", validate_template_device)

    # TODO: Optional cleanup on col.endex().
    # from colosseum_template.connections import close_all
    # registry.register_shutdown(close_all)
