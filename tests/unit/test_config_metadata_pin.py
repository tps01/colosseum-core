"""CLI-pinned config/metadata: script loads need force=True."""

from __future__ import annotations

from pathlib import Path

from colosseum.config import load_config
from colosseum.config.metadata import load_metadata
from colosseum.context import get_context, init_context


def _write_toml(path: Path, label: str) -> Path:
    path.write_text(f'[runtime]\nlabel = "{label}"\n', encoding="utf-8")
    return path


def _write_meta(path: Path, uut: str) -> Path:
    path.write_text(f"test_metadata:\n  uut: {uut}\n", encoding="utf-8")
    return path


def test_config_pin_skips_script_load_without_force(tmp_path) -> None:
    cli = _write_toml(tmp_path / "cli.toml", "from-cli")
    other = _write_toml(tmp_path / "other.toml", "from-script")
    init_context(test_case_name="pin_cfg", config_path=cli)
    load_config(cli)
    get_context().session.config_pinned = True

    store = load_config(other)
    assert store.get_section("runtime.label") == "from-cli"
    assert Path(str(get_context().config_path)).resolve() == cli.resolve()
    assert get_context().session.config_pin_warned is True

    # Second skip keeps the one-shot warn latch (does not reset / re-warn)
    load_config(other)
    assert get_context().session.config_pin_warned is True


def test_config_pin_force_replaces(tmp_path) -> None:
    cli = _write_toml(tmp_path / "cli.toml", "from-cli")
    other = _write_toml(tmp_path / "other.toml", "from-script")
    init_context(test_case_name="pin_force", config_path=cli)
    load_config(cli)
    get_context().session.config_pinned = True

    store = load_config(other, force=True)
    assert store.get_section("runtime.label") == "from-script"
    assert Path(str(get_context().config_path)).resolve() == other.resolve()
    # Pin remains; non-force still blocked
    load_config(cli)
    assert get_context().config.get_section("runtime.label") == "from-script"


def test_unpinned_second_load_config_replaces(tmp_path) -> None:
    first = _write_toml(tmp_path / "a.toml", "a")
    second = _write_toml(tmp_path / "b.toml", "b")
    load_config(first)
    store = load_config(second)
    assert store.get_section("runtime.label") == "b"


def test_metadata_pin_skips_without_force(tmp_path) -> None:
    cfg = _write_toml(tmp_path / "c.toml", "x")
    m1 = _write_meta(tmp_path / "m1.yaml", "CLI_UUT")
    m2 = _write_meta(tmp_path / "m2.yaml", "SCRIPT_UUT")
    init_context(test_case_name="pin_meta", config_path=cfg)
    load_config(cfg)
    load_metadata(m1)
    get_context().session.metadata_pinned = True

    out = load_metadata(m2)
    assert out.get("uut") == "CLI_UUT"
    assert get_context().metadata_yaml.get("uut") == "CLI_UUT"
    assert get_context().session.metadata_pin_warned is True


def test_metadata_pin_force_replaces(tmp_path) -> None:
    cfg = _write_toml(tmp_path / "c.toml", "x")
    m1 = _write_meta(tmp_path / "m1.yaml", "CLI_UUT")
    m2 = _write_meta(tmp_path / "m2.yaml", "SCRIPT_UUT")
    init_context(test_case_name="pin_meta_force", config_path=cfg)
    load_config(cfg)
    load_metadata(m1)
    get_context().session.metadata_pinned = True

    out = load_metadata(m2, force=True)
    assert out.get("uut") == "SCRIPT_UUT"


def test_config_pin_does_not_block_metadata(tmp_path) -> None:
    cfg = _write_toml(tmp_path / "c.toml", "cli")
    other = _write_toml(tmp_path / "o.toml", "script")
    m1 = _write_meta(tmp_path / "m1.yaml", "ONE")
    init_context(test_case_name="indep", config_path=cfg)
    load_config(cfg)
    get_context().session.config_pinned = True

    load_config(other)  # skipped
    load_metadata(m1)  # metadata not pinned — applies
    assert get_context().config.get_section("runtime.label") == "cli"
    assert get_context().metadata_yaml.get("uut") == "ONE"


def test_metadata_pin_does_not_block_config(tmp_path) -> None:
    cfg = _write_toml(tmp_path / "c.toml", "first")
    other = _write_toml(tmp_path / "o.toml", "second")
    m1 = _write_meta(tmp_path / "m1.yaml", "META")
    m2 = _write_meta(tmp_path / "m2.yaml", "OTHER")
    init_context(test_case_name="indep2", config_path=cfg)
    load_config(cfg)
    load_metadata(m1)
    get_context().session.metadata_pinned = True

    assert load_metadata(m2).get("uut") == "META"
    load_config(other)  # config not pinned — replaces
    assert get_context().config.get_section("runtime.label") == "second"


def test_pinned_load_config_skips_nested_metadata_kwarg(tmp_path) -> None:
    """Skipped load_config must not apply metadata_path either."""
    cfg = _write_toml(tmp_path / "c.toml", "cli")
    other = _write_toml(tmp_path / "o.toml", "script")
    m_cli = _write_meta(tmp_path / "m_cli.yaml", "CLI_META")
    m_script = _write_meta(tmp_path / "m_script.yaml", "SCRIPT_META")
    init_context(test_case_name="nested", config_path=cfg)
    load_config(cfg, metadata_path=m_cli)
    get_context().session.config_pinned = True
    get_context().session.metadata_pinned = True

    load_config(other, metadata_path=m_script)
    assert get_context().config.get_section("runtime.label") == "cli"
    assert get_context().metadata_yaml.get("uut") == "CLI_META"
