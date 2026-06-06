"""read_relaxed_toml helper."""

from __future__ import annotations

from pathlib import Path

from colosseum.config.toml_relaxed import read_relaxed_toml


def test_read_relaxed_toml_strips_bom(tmp_path: Path) -> None:
    config_path = tmp_path / "bom.toml"
    config_path.write_bytes(
        b"\xef\xbb\xbf"
        b"[[equipment.psu]]\n"
        b"psu_id = 1\n"
        b"driver = sim\n"
    )
    raw = read_relaxed_toml(config_path)
    assert raw["equipment"]["psu"][0]["driver"] == "sim"
