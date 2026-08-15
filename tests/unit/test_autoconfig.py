"""Unit tests for col.equipment.autoconfig()."""

from __future__ import annotations

from pathlib import Path

import colosseum.context as context_module
import pytest
from colosseum.config.loader import ConfigError
from colosseum.context import get_context
from colosseum_equipment.api._autoconfig import autoconfig
from colosseum_equipment.autoconfig.discovery import discover_equipment_config
from colosseum_shared.network import IPv4NetworkBinding


class _FakeInstrument:
    def __init__(self, idn: str) -> None:
        self.timeout = 0
        self._idn = idn
        self.closed = False

    def query(self, command: str) -> str:
        if command == "*IDN?":
            return self._idn
        raise RuntimeError(f"unexpected query: {command}")

    def close(self) -> None:
        self.closed = True


class _FakeResourceManager:
    def __init__(self, resources: dict[str, str]) -> None:
        self._resources = resources
        self.opened: list[_FakeInstrument] = []

    def list_resources(self, query: str) -> tuple[str, ...]:
        _ = query
        return tuple(self._resources)

    def open_resource(self, resource: str) -> _FakeInstrument:
        if resource not in self._resources:
            raise RuntimeError(f"unknown resource: {resource}")
        inst = _FakeInstrument(self._resources[resource])
        self.opened.append(inst)
        return inst


def test_discover_assigns_ids_by_connection_order() -> None:
    rm = _FakeResourceManager(
        {
            "GPIB0::1::INSTR": "TDK-Lambda,GENESYS-28-80,1,1",
            "TCPIP0::192.168.1.29::INSTR": "TDK-Lambda,GENESYS-28-80,2,1",
            "GPIB0::2::INSTR": "Keysight Technologies,EDU34450A,1,1",
        }
    )
    result = discover_equipment_config(resource_manager=rm, timeout=1.0)
    psu_rows = result.raw["equipment"]["psu"]
    assert len(psu_rows) == 2
    assert psu_rows[0]["psu_id"] == 1
    assert psu_rows[0]["resource"].startswith("TCPIP")
    assert psu_rows[1]["psu_id"] == 2
    assert psu_rows[1]["resource"].startswith("GPIB")
    assert result.raw["equipment"]["dmm"][0]["dmm_id"] == 1
    assert all(inst.closed for inst in rm.opened)


def test_discover_blacklist_excludes_tcpip_subnet() -> None:
    rm = _FakeResourceManager(
        {
            "TCPIP0::10.0.0.42::INSTR": "TDK-Lambda,GENESYS-28-80,1,1",
            "GPIB0::1::INSTR": "TDK-Lambda,GENESYS-28-80,2,1",
        }
    )
    bindings = [
        IPv4NetworkBinding(
            interface="eth0",
            address="10.0.0.5",
            network="10.0.0.0",
            prefix=24,
        )
    ]
    result = discover_equipment_config(
        resource_manager=rm,
        blacklist="eth0",
        network_bindings=bindings,
        timeout=1.0,
    )
    assert len(result.blacklisted) == 1
    assert len(result.assignments) == 1
    assert result.assignments[0].resource.startswith("GPIB")


def test_discover_raises_when_no_classifiable_resources() -> None:
    rm = _FakeResourceManager({"GPIB0::1::INSTR": "UNKNOWN,WIDGET,1,1"})
    with pytest.raises(ConfigError, match="no classifiable"):
        discover_equipment_config(resource_manager=rm, timeout=1.0)


def test_autoconfig_populates_config_store(monkeypatch: pytest.MonkeyPatch) -> None:
    import colosseum_equipment.api._autoconfig as autoconfig_module

    context_module._ACTIVE_CONTEXT = None
    rm = _FakeResourceManager(
        {"GPIB0::1::INSTR": "Keysight Technologies,EDU34450A,1,1"}
    )

    def _fake_discover(**kwargs: object) -> object:
        return discover_equipment_config(
            resource_manager=rm,
            timeout=float(kwargs.get("timeout", 5.0)),  # type: ignore[arg-type]
            blacklist=kwargs.get("blacklist"),  # type: ignore[arg-type]
        )

    monkeypatch.setattr(autoconfig_module, "discover_equipment_config", _fake_discover)
    store = autoconfig(timeout=1.0)
    ctx = get_context()
    assert ctx is not None
    assert ctx.config_path == "(autoconfig)"
    assert store.require_item("equipment.dmm", 1)["model"] == "keysight-edu34450a"


def test_autoconfig_export_writes_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import colosseum_equipment.api._autoconfig as autoconfig_module

    from colosseum.config.toml_relaxed import read_relaxed_toml
    from colosseum.context import init_context, require_context
    from colosseum.output import ensure_output_dir

    context_module._ACTIVE_CONTEXT = None
    init_context(test_case_name="export_test")
    ensure_output_dir(require_context())
    rm = _FakeResourceManager(
        {"GPIB0::1::INSTR": "Keysight Technologies,EDU34450A,1,1"}
    )

    def _fake_discover(**kwargs: object) -> object:
        return discover_equipment_config(
            resource_manager=rm,
            timeout=float(kwargs.get("timeout", 5.0)),  # type: ignore[arg-type]
            blacklist=kwargs.get("blacklist"),  # type: ignore[arg-type]
        )

    monkeypatch.setattr(autoconfig_module, "discover_equipment_config", _fake_discover)
    export_path = tmp_path / "bench.generated.toml"
    autoconfig(timeout=1.0, export_path=export_path)
    ctx = require_context()
    assert export_path.is_file()
    loaded = read_relaxed_toml(export_path)
    dmm_section = loaded["equipment"]["dmm"]
    row = dmm_section[0] if isinstance(dmm_section, list) else dmm_section
    assert row["model"] == "keysight-edu34450a"
    metadata = {row.key: row.value for row in ctx.db.fetch_run_metadata()}
    assert metadata["config_export_path"] == str(export_path.resolve())
