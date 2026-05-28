"""U-PLG-01: plugin registry contracts."""

from __future__ import annotations

from colosseum.config.sections import ConfigSectionSpec
from colosseum.plugins.registry import PluginRegistry


def test_shutdown_hooks_run_in_reverse_order() -> None:
    reg = PluginRegistry()
    order: list[int] = []
    reg.register_shutdown(lambda: order.append(1))
    reg.register_shutdown(lambda: order.append(2))
    reg.run_shutdown()
    assert order == [2, 1]


def test_replacing_section_spec_logs_warning(caplog) -> None:
    reg = PluginRegistry()
    spec = ConfigSectionSpec("equipment.psu", "psu_id", ("driver",))
    reg.register_config_section(spec)
    reg.register_config_section(spec)
    assert any("Replacing config section" in r.message for r in caplog.records)
