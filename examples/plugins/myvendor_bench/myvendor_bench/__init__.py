"""Example Colosseum extension package (reference skeleton)."""

from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins.registry import PluginRegistry


def register(registry: PluginRegistry) -> None:
    from myvendor_bench import api

    registry.register_namespace("myvendor", api)
    registry.register_config_section(
        ConfigSectionSpec(
            "myvendor.fixture",
            "fixture_id",
            required_keys=("serial",),
            optional_keys=("label",),
        )
    )
