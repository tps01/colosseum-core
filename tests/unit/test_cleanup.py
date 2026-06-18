from scripts.cleanup import _collect_paths


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("generated", encoding="utf-8")


def test_cleanup_keeps_venv_extension_modules(tmp_path):
    _touch(tmp_path / ".venv" / "Lib" / "site-packages" / "native.pyd")
    _touch(tmp_path / ".venv" / "Lib" / "site-packages" / "module.pyc")

    targets = {
        path.relative_to(tmp_path).as_posix()
        for path in _collect_paths(tmp_path, include_venvs=False, include_infra=False)
    }

    assert ".venv/Lib/site-packages/native.pyd" not in targets
    assert ".venv/Lib/site-packages/module.pyc" in targets


def test_cleanup_matches_share_and_infra_ignore_policy(tmp_path):
    _touch(tmp_path / "share" / "notes.txt")
    _touch(tmp_path / "share" / "python-wheels" / "package.whl")
    _touch(tmp_path / "infra" / "yocto" / "artifacts" / ".gitkeep")
    _touch(tmp_path / "infra" / "yocto" / "artifacts" / "qemu.log")

    targets = {
        path.relative_to(tmp_path).as_posix()
        for path in _collect_paths(tmp_path, include_venvs=False, include_infra=True)
    }

    assert "share" not in targets
    assert "share/notes.txt" not in targets
    assert "share/python-wheels" in targets
    assert "infra/yocto/artifacts/.gitkeep" not in targets
    assert "infra/yocto/artifacts/qemu.log" in targets
