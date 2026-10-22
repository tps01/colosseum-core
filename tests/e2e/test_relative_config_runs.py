"""Config paths follow scripts under direct, CLI, and suite execution."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize("mode", ["direct", "cli", "suite"])
def test_relative_loads_follow_each_script(tmp_path, subprocess_env, mode):
    caller = tmp_path / "caller"
    caller.mkdir()
    scripts = []
    for name in ("setup", "test", "between", "teardown"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "config.toml").write_text(f'[runtime]\nlabel = "{name}"\n', encoding="utf-8")
        (directory / "metadata.yaml").write_text(f"uut: {name}\n", encoding="utf-8")
        script_dir = directory / "scripts"
        script_dir.mkdir()
        script = script_dir / "case.py"
        script.write_text(
            "import colosseum as col\n"
            "from colosseum.context import get_context\n"
            "# Module loading and main() both have script-relative paths.\n"
            'col.config.load_config("../config.toml", no_artifacts=(__name__ == "__main__"), '
            'metadata_path="../metadata.yaml")\n'
            "def main():\n"
            '    col.config.load_metadata("../metadata.yaml")\n'
            f'    assert col.config.get("runtime.label") == "{name}"\n'
            f'    assert get_context().metadata_yaml["uut"] == "{name}"\n'
            'if __name__ == "__main__":\n'
            "    main()\n"
            "    col.endex()\n",
            encoding="utf-8",
        )
        scripts.append(script)
    if mode == "direct":
        args = [str(scripts[0])]
    elif mode == "cli":
        args = ["-m", "colosseum.runner.cli", "run", str(scripts[0]), "--no-artifacts"]
    else:
        suite = tmp_path / "suite.toml"
        suite.write_text(
            f'name = "paths"\nsetup = ["{scripts[0].as_posix()}"]\n'
            f'tests = ["{scripts[1].as_posix()}", "{scripts[1].as_posix()}"]\n'
            f'between_tests = ["{scripts[2].as_posix()}"]\n'
            f'teardown = ["{scripts[3].as_posix()}"]\n',
            encoding="utf-8",
        )
        args = ["-m", "colosseum.runner.cli", "run-suite", str(suite), "--no-artifacts"]
    proc = subprocess.run(
        [sys.executable, *args], cwd=caller, env=subprocess_env,
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_cli_config_path_does_not_fallback_to_script(tmp_path, subprocess_env):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "config.toml").write_text("", encoding="utf-8")
    script = scripts / "case.py"
    script.write_text("def main():\n    pass\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "colosseum.runner.cli", "run", str(script), "-g", "config.toml"],
        cwd=tmp_path, env=subprocess_env, capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode != 0
    assert "Config file not found" in proc.stdout + proc.stderr
