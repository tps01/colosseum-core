"""Colosseum shared utilities plugin (SSH, regex, parsing)."""

__colosseum_domain__ = "shared"

from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins.registry import PluginRegistry

from colosseum_shared.connections import close_all


def register(registry: PluginRegistry) -> None:
    from colosseum_shared import api

    registry.register_namespace("shared", api)
    registry.register_shutdown(close_all)
    registry.register_config_section(
        ConfigSectionSpec(
            "shared.ssh",
            "ssh_id",
            required_keys=("host", "username"),
            optional_keys=("port", "password", "key_filename", "timeout", "driver"),
        )
    )
