"""Minimal good plugin for core plugin-contract e2e tests."""

from __future__ import annotations

from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins.registry import PluginRegistry

__colosseum_domain__ = "contract_probe"


def register(registry: PluginRegistry) -> None:
    from colosseum_contract_probe import api

    registry.register_namespace("contract_probe", api)
    registry.register_config_section(
        ConfigSectionSpec(
            dotted_path="contract_probe.device",
            id_field="device_id",
            required_keys=("serial",),
            optional_keys=("label",),
        ),
    )
