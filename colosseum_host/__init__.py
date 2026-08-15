"""Colosseum host plugin (bench PC prerequisites)."""

__colosseum_domain__ = "host"

from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins.registry import PluginRegistry


def register(registry: PluginRegistry) -> None:
    from colosseum_host import api

    registry.register_namespace("host", api)
    registry.register_config_section(
        ConfigSectionSpec(
            "host.profile",
            "profile_id",
            required_keys=(),
            optional_keys=(
                "min_disk_gb",
                "min_memory_mb",
                "python_version_prefix",
                "platform",
                "disk_path",
            ),
        )
    )
