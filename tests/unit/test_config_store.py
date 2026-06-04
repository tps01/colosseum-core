"""U-CFG-04: ConfigStore lookups."""

from __future__ import annotations

import pytest

import colosseum as col
from colosseum.config.loader import ConfigError, ConfigStore, load_config
from colosseum.config.sections import ConfigSectionSpec
from colosseum.context import require_context
from colosseum.output import ensure_output_dir


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


def test_load_config_wraps_normalization_errors(tmp_path) -> None:
    config_path = tmp_path / "bad.toml"
    config_path.write_text(
        "[[equipment.psu]]\n"
        "psu_id = 1\n"
        "driver = \"sim\"\n"
        "resource = \"A\"\n"
        "\n"
        "[[equipment.psu]]\n"
        "psu_id = 1\n"
        "driver = \"sim\"\n"
        "resource = \"B\"\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="Duplicate id"):
        load_config(config_path)


def test_load_config_accepts_utf8_bom(tmp_path) -> None:
    config_path = tmp_path / "bom.toml"
    config_path.write_bytes(
        b"\xef\xbb\xbf"
        b"[[equipment.psu]]\n"
        b"psu_id = 1\n"
        b"driver = \"sim\"\n"
        b"resource = \"SIM::1\"\n"
    )

    store = load_config(config_path)

    assert store.get_equipment("psu", 1)["resource"] == "SIM::1"


def test_config_is_loaded_reports_runtime_state(bench_sim) -> None:
    assert col.config.is_loaded() is False

    load_config(bench_sim)

    assert col.config.is_loaded() is True


def test_load_config_reload_updates_run_metadata(bench_sim, isolated_cwd, tmp_path) -> None:
    load_config(bench_sim)
    ctx = require_context()
    ensure_output_dir(ctx)
    replacement = tmp_path / "replacement.toml"
    replacement.write_text(
        "[[equipment.psu]]\n"
        "psu_id = 1\n"
        "driver = \"sim\"\n"
        "resource = \"SIM::REPLACEMENT\"\n",
        encoding="utf-8",
    )

    load_config(replacement)

    metadata = {row.key: row.value for row in ctx.db.fetch_run_metadata()}
    assert metadata["config_path"] == str(replacement.resolve())
