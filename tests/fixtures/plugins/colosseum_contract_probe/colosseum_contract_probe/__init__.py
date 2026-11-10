"""Minimal good plugin for core plugin-contract e2e tests."""

from __future__ import annotations

from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins.registry import PluginRegistry
from colosseum.plugins.lazy import lazy_module

__colosseum_domain__ = "contract_probe"


def register(registry: PluginRegistry) -> None:
    api = lazy_module("colosseum_contract_probe.api")

    registry.register_namespace("contract_probe", api)
    registry.register_shutdown(lambda: api.shutdown())
    registry.register_listener("contract_probe", lambda output, result, ctx: api.report(output, result, ctx))
    registry.register_config_section(
        ConfigSectionSpec(
            dotted_path="contract_probe.device",
            id_field="device_id",
            required_keys=("serial",),
            optional_keys=("label",),
        ),
    )
