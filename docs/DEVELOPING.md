# Developing Colosseum

Guide for contributors and maintainers working in this repository. End users should start with the [top-level README](../README.md).

## Environment setup

Clone the repository, then create a virtual environment and install editable runtime plus dev tools:

```sh
git clone https://github.com/tps01/colosseum.git
cd colosseum
```

| Shell | Command |
|-------|---------|
| Windows PowerShell | `. .\scripts\start_environment.ps1` |
| Windows `cmd.exe` | `scripts\start_environment.bat` |
| Linux / macOS | `. ./scripts/start_environment.sh` |

On Windows, run tests with `python scripts/run_tests.py` (or `.\.venv\Scripts\python.exe scripts\run_tests.py`). Do not use `py`: the launcher ignores the venv and can pick PyPy via the `#!/usr/bin/env python3` shebang. `start_environment.bat` cannot activate a PowerShell session; use the `.ps1` helper or the `.venv` interpreter directly.

Runtime only (no pytest or Sphinx tools): set `SKIP_DEV=1` before the script, or:

```sh
python -m venv .venv
# activate .venv, then:
python -m pip install -U pip setuptools wheel
python -m pip install -e .
python -m pip install -r requirements-dev.txt   # omit for runtime-only
```

`requirements-dev.txt` installs the `test`, `docs`, `static`, and `plot` extras (pytest, Sphinx, ruff/mypy/bandit/vulture, matplotlib).

Smoke the sim path:

```sh
colosseum run examples/test_power_rails.py --config examples/configs/bench.sim.toml
```

## Host dependencies for developers

| What you want | Install | Host / OS notes |
|---------------|---------|-----------------|
| Default unit/integration/e2e | `requirements-dev.txt` | None beyond Python |
| PyVISA-sim tests (`pytest -m visa_sim`) | `pip install -e ".[test]"` | **Python 3.10+**; no lab VISA |
| RF visa-sim integration | `examples/configs/bench.rf.visa-sim.toml` | Dev install + Python 3.10+ |
| Build HTML docs | `requirements-dev.txt` | None |
| Build PDF docs (`build_all.py` default) | Dev requirements + Sphinx | `latexmk` + TeX (MiKTeX/TeX Live on Windows; `texlive-*` on Ubuntu — see [CI docgen job](../.github/workflows/ci.yml)) |
| Build offline release bundle | Source checkout + `scripts/package_offline.py` | Network; same Python **minor** as the target bench |

Do not rely on offline tarballs for pytest, Sphinx, docgen, or PyVISA-sim — those tools are intentionally omitted from air-gapped runtime bundles.

## Common commands

```sh
python scripts/run_tests.py              # pytest tiers 1–3
python -m pytest tests/unit              # unit tests only
pytest -m visa_sim -q                    # PyVISA-sim (3.10+, .[test] extra)
python scripts/run_static.py             # ruff, mypy, bandit, vulture
python scripts/run_tests.py --regression --skip-offline   # soak + docgen
python scripts/docgen/build_all.py       # HTML + PDF; --skip-pdf without LaTeX
python scripts/cleanup.py --dry-run      # preview removal of outputs/, build/, caches
py -3.11 scripts/package_offline.py      # runtime offline bundle for that interpreter
```

Agent-oriented regression notes: [AGENTS.md](../AGENTS.md).

## CI

GitHub Actions runs pytest on Windows and Ubuntu (3.9 skips `visa_sim`, 3.11 full), a dedicated `visa_sim` job on 3.10+, docgen PDF artifact, offline bundle smoke, and packaging smoke. Pages docs: manual [Documentation workflow](../.github/workflows/docs.yml) (`workflow_dispatch`).

Release tags (`v*`) run the [Release workflow](../.github/workflows/release.yml); see [releasing.md](releasing.md).

## Further reading

| Topic | Location |
|-------|----------|
| Testing tiers, profiling, static analysis | [testing/README.md](testing/README.md) |
| Hardware regression procedure | [testing/regression-test-procedure.md](testing/regression-test-procedure.md) |
| Docgen pipeline | [../scripts/docgen/README.md](../scripts/docgen/README.md) |
| Implementation scope | [scope.md](scope.md) |
| Docs index | [README.md](README.md) |
| Historical planning recovery | [archive/README.md](archive/README.md) |
