"""U-CFG-04: ConfigStore lookups."""

from __future__ import annotations

import pytest

from colosseum.config.loader import ConfigError, ConfigStore
from colosseum.config.sections import ConfigSectionSpec


SPEC = ConfigSectionSpec(
    dotted_path="equipment.psu",
    id_field="psu_id",
    required_keys=("driver", "resource"),
)


def _store() -> ConfigStore:
    normalized = {
        "equipment.psu": {
            1: {"psu_id": 1, "driver": "sim", "resource": "SIM::1"},
        }
    }
    return ConfigStore({}, normalized, {SPEC.dotted_path: SPEC})


def test_get_item_returns_row() -> None:
    row = _store().get_item("equipment.psu", 1)
    assert row["resource"] == "SIM::1"


def test_unknown_id_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="Unknown id"):
        _store().get_item("equipment.psu", 99)


def test_require_item_checks_required_keys() -> None:
    store = ConfigStore(
        {},
        {"equipment.psu": {1: {"psu_id": 1, "driver": "sim"}}},
        {SPEC.dotted_path: SPEC},
    )
    with pytest.raises(ConfigError, match="missing required keys"):
        store.require_item("equipment.psu", 1)
