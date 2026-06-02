# Colosseum

Python test automation for embedded and bench system testing. Scripts use `import colosseum as col`, call measurement and verification APIs, and finish with **`col.endex()`** so logs, SQLite evidence, summaries, cleanup, and exit status are consistent.

**Python:** 3.9+ (3.11 recommended for new Windows/Linux benches). **Status:** [MVP scope](docs/mvp/scope.md).

---

## Get started

Pick one path below. All paths install the same runtime (`colosseum` CLI, equipment/shared plugins, sim and PyVISA-sim support).

### 1. Clone from Git (development)

```sh
git clone https://github.com/tps01/colosseum.git
cd colosseum
```

Create a virtual environment and install (editable runtime + dev tools):

| Shell | Command |
|-------|---------|
| Windows PowerShell | `.\scripts\start_environment.ps1` |
| Windows `cmd.exe` | `scripts\start_environment.bat` |
| Linux / macOS | `. ./scripts/start_environment.sh` |

Runtime only (no pytest, Sphinx, mutation tools): set `SKIP_DEV=1` before the script, or:

```sh
python -m venv .venv
# activate .venv, then:
python -m pip install -U pip setuptools wheel
python -m pip install -e .
python -m pip install -r requirements-dev.txt   # omit for runtime-only
```

**First run (no hardware):**

```sh
colosseum run examples/test_power_rails.py --config examples/configs/bench.sim.toml
```

Each run writes `outputs/<timestamp>_<name>/` with `debug.log`, `execution.sqlite`, `summary.txt`, and `summary.json`.

### 2. Install from a tagged GitHub release

Pushing a tag `v*` (for example `v0.3.0`) runs the [Release workflow](.github/workflows/release.yml), which builds the files below. Download them from **[Releases](https://github.com/tps01/colloseum/releases)** for that tag when published, or from the workflow run **Artifacts** until they are attached to the release. CI also produces a documentation PDF on each main-branch run ([docgen job](.github/workflows/ci.yml)); attach `colosseum.pdf` to the release when publishing.

| Asset | Use |
|-------|-----|
| `colosseum-<ver>-py3-none-any.whl` | Online install: `pip install colosseum-<ver>-py3-none-any.whl` |
| `colosseum-<ver>.tar.gz` (sdist) | `pip install colosseum-<ver>.tar.gz` or build wheels on another platform |
| `colosseum-<ver>-offline-<os>-<arch>-pyXY.tar.gz` | Air-gapped bench: extract, venv, `pip install --no-index --find-links=wheels colosseum==<ver>` |
| `colosseum.pdf` (when published on the release) | Offline user / API reference; same content as CI docgen PDF |

Offline bundles are built per OS and Python minor (`py39`, `py311`, etc.). The `pyXY` in the filename **must match** the interpreter in your venv. After install, smoke-test with the files inside the bundle:

```sh
colosseum run smoke/run_sim.py --config smoke/bench.sim.toml
```

Full steps (Windows/Linux, Docker check, regression): [offline install guide](docs/sphinx/source/guides/offline_install.rst) (also in generated HTML under **Guides → Offline install**).

To build a bundle yourself from a connected checkout:

```sh
py -3.11 scripts/package_offline.py          # Linux/Windows bundle for that interpreter
py -3.11 scripts/package_offline.py --include-dev   # optional: pytest, Sphinx, Cosmic Ray wheels
```

### 3. PyPI (when published)

```sh
pip install colosseum
```

PyPI may lag GitHub releases; use **Releases** for offline tarballs and version-pinned wheels.

---

## Host dependencies by capability

Pip installs Python packages; the host still needs OS/runtime pieces for some features.

| What you want | Colosseum install | Host / OS (not from pip) |
|---------------|-------------------|---------------------------|
| Simulated bench, CI, examples with `bench.sim.toml` | Default `colosseum` package | None beyond Python |
| VISA instruments (`driver` omitted or `visa` in bench TOML) | `pyvisa` (included) | IVI-compatible VISA (NI, Keysight, Tek, R&S, …) or `pyvisa-py`; optional `visa_library` per instrument — see [platform notes](docs/sphinx/source/guides/platform_notes.rst) |
| Serial instruments (`driver = "serial"`) | `pyserial` (included) | Correct `COM*` (Windows) or `/dev/ttyUSB*` (Linux); Linux: `dialout` or udev |
| SSH / remote shell (`col.shared`) | `paramiko` (included) | Network reachability; keys/credentials in bench config |
| GUI runner (`colosseum --gui`) | `customtkinter` (included) | Display; Linux: `python3-tk` |
| PyVISA-sim tests (`pytest -m visa_sim`) | `pyvisa-sim` (included) | **Python 3.10+**; no lab VISA |
| RF examples offline | `examples/configs/bench.rf.visa-sim.toml` | Python 3.10+ for visa_sim marker tests |
| Build HTML docs | `pip install -r requirements-dev.txt` | None |
| Build PDF docs (`build_all.py` default) | Dev requirements + Sphinx | `latexmk` + TeX (MiKTeX/TeX Live on Windows; `texlive-*` on Ubuntu — see [CI docgen job](.github/workflows/ci.yml)) |
| Build offline release bundle | Source checkout + `scripts/package_offline.py` | Network; same Python **minor** as target bench |

Verify VISA after install: `python -m pyvisa info` inside your venv.

---

## Direct Python scripts

CLI (`colosseum run` / `run-suite`) is preferred for suites and shared bench config. Direct scripts must call `col.endex()` themselves:

```python
import colosseum as col

def main() -> None:
    col.config.load_config("examples/configs/bench.sim.toml")
    col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
    col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)

if __name__ == "__main__":
    main()
    col.endex()
```

**Suite example:**

```sh
colosseum run-suite tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml
```

---

## Development and CI

```sh
python -m pytest tests/unit              # unit tests only
python scripts/run_tests.py              # default tiers 1–3
pytest -m visa_sim -q                      # PyVISA-sim (Python 3.10+)
python scripts/docgen/build_all.py       # HTML + PDF; --skip-pdf without LaTeX
python scripts/cleanup.py --dry-run      # remove outputs/, build/, caches
```

GitHub Actions: pytest on Windows and Ubuntu (3.9, 3.11), `visa_sim` on 3.10+, docgen PDF artifact, offline bundle smoke, packaging smoke. Pages docs: manual [Documentation workflow](.github/workflows/docs.yml) (`workflow_dispatch`).

Details: [testing guide](docs/testing/README.md), [regression procedure](docs/testing/regression-test-procedure.md).

---

## Documentation

| Topic | Location |
|-------|----------|
| User guides (install, config, RF, offline) | [docs/sphinx/source/guides/](docs/sphinx/source/guides/) |
| Local HTML/PDF build | `python scripts/docgen/build_all.py` → `build/docgen/site/html/`, `build/docgen/site/latex/colosseum.pdf` |
| Docgen pipeline | [scripts/docgen/README.md](scripts/docgen/README.md) |
| Design / MVP / archive | [docs/README.md](docs/README.md), [docs/mvp/scope.md](docs/mvp/scope.md), [docs/archive/README.md](docs/archive/README.md) |

---

## License

MIT — see [LICENSE](LICENSE).
