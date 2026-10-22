"""Config/metadata paths resolve consistently without changing process cwd."""

from pathlib import Path

import pytest

from colosseum.config import ConfigError, load_config, load_metadata


@pytest.fixture
def path_layout(unit_runtime_context, tmp_path, monkeypatch):
    caller = tmp_path / "caller"
    scripts = tmp_path / "bench" / "scripts"
    caller.mkdir()
    scripts.mkdir(parents=True)
    monkeypatch.chdir(caller)
    unit_runtime_context.active_script_path = scripts / "case.py"
    return unit_runtime_context, caller, scripts


@pytest.mark.parametrize("location", ["script", "working", "absolute"])
def test_config_and_metadata_use_same_resolution(path_layout, location):
    ctx, caller, scripts = path_layout
    base = caller if location == "working" else scripts.parent
    config = base / "config.toml"
    metadata = base / "metadata.yaml"
    config.write_text('[runtime]\nlabel = "loaded"\n', encoding="utf-8")
    metadata.write_text("test_metadata:\n  uut: loaded\n", encoding="utf-8")
    if location == "absolute":
        config_arg, metadata_arg = config, metadata
    elif location == "script":
        config_arg, metadata_arg = "../config.toml", "../metadata.yaml"
    else:
        config_arg, metadata_arg = "config.toml", "metadata.yaml"
    store = load_config(config_arg, metadata_path=metadata_arg)
    assert store.get_section("runtime.label") == "loaded"
    assert ctx.config_path == str(config)
    assert ctx.metadata_path == str(metadata)
    assert ctx.metadata_yaml["uut"] == "loaded"
    assert Path.cwd() == caller


@pytest.mark.parametrize("kind", ["config", "metadata"])
def test_working_directory_wins_and_parse_errors_do_not_fallback(path_layout, kind):
    ctx, caller, scripts = path_layout
    filename = "config.toml" if kind == "config" else "metadata.yaml"
    load = load_config if kind == "config" else load_metadata
    valid = '[runtime]\nlabel = "script"\n' if kind == "config" else "uut: script\n"
    (scripts / filename).write_text(valid, encoding="utf-8")
    selected = caller / filename
    selected.write_text(valid.replace("script", "working"), encoding="utf-8")
    load(filename)
    assert (ctx.config_path if kind == "config" else ctx.metadata_path) == str(selected)
    selected.write_text("[broken", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid TOML|Invalid YAML") as error:
        load(filename)
    assert str(selected) in str(error.value)


@pytest.mark.parametrize("load,filename", [(load_config, "lost.toml"), (load_metadata, "lost.yaml")])
def test_missing_paths_report_both_locations(path_layout, load, filename):
    _, caller, scripts = path_layout
    with pytest.raises(ConfigError) as error:
        load(filename)
    assert str(caller / filename) in str(error.value)
    assert str(scripts / filename) in str(error.value)
    absolute = caller / filename
    with pytest.raises(ConfigError) as error:
        load(absolute)
    assert str(scripts / filename) not in str(error.value)


def test_pins_skip_missing_paths_and_force_resolves_script_paths(path_layout):
    ctx, _, scripts = path_layout
    config = scripts / "config.toml"
    metadata = scripts / "metadata.yaml"
    config.write_text('[runtime]\nlabel = "script"\n', encoding="utf-8")
    metadata.write_text("uut: script\n", encoding="utf-8")
    load_config(config, metadata_path=metadata)
    ctx.session.config_pinned = True
    ctx.session.metadata_pinned = True
    assert load_config("missing.toml").get_section("runtime.label") == "script"
    assert load_metadata("missing.yaml")["uut"] == "script"
    # A config reload must not resolve or overwrite separately pinned metadata.
    ctx.session.config_pinned = False
    load_config("config.toml", metadata_path="missing.yaml")
    assert ctx.metadata_path == str(metadata)
    load_config("config.toml", metadata_path="metadata.yaml", force=True)
    assert ctx.metadata_path == str(metadata)
    assert load_metadata("metadata.yaml", force=True)["uut"] == "script"
