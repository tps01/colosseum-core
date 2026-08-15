# Colosseum

Python test automation for embedded and bench system testing. Scripts use `import colosseum as col`, call measurement and verification APIs, and finish with **`col.endex()`** so logs, SQLite evidence, summaries, cleanup, and exit status are consistent.

**Python:** 3.9+ (3.11 recommended for new Windows/Linux benches). **Status:** [implementation scope](docs/scope.md).

Contributing or working on the repository itself? See the [developer guide](docs/DEVELOPING.md).

---

## Install

Pick one path. All paths install the same runtime (`colosseum` CLI, equipment/shared plugins, and in-process sim drivers).

### From a GitHub release

Tagged releases (`v*`) publish assets on **[Releases](https://github.com/tps01/colloseum/releases)**:

| Asset | Use |
|-------|-----|
| `colosseum-<ver>-py3-none-any.whl` | Online install: `pip install colosseum-<ver>-py3-none-any.whl` |
| `colosseum-<ver>.tar.gz` (sdist) | `pip install colosseum-<ver>.tar.gz` |
| `colosseum-<ver>-offline-<os>-<arch>-pyXY.tar.gz` | Air-gapped **bench** (runtime wheels only) |
| `colosseum.pdf` | End-user run guide + public API |
| `colosseum-docs-html.zip` | Same documentation as browsable HTML |

Offline bundles are built per OS and Python minor (`py39`, `py311`, etc.). The `pyXY` in the filename **must match** the interpreter in your venv.

**Windows:** Right-click the `.tar.gz` → **Extract All**, open `offline-bundle`, then run `.\install.ps1` or `install.bat`.

**Linux:** `tar xzf colosseum-*-offline-*.tar.gz`, `cd offline-bundle`, `./install.sh`.

Smoke-test after install:

```sh
colosseum run smoke/run_sim.py --config smoke/bench.sim.toml
```

Full steps: [offline install guide](docs/sphinx/source/guides/offline_install.rst) (also in generated HTML under **Guides → Offline install**).

### From PyPI (when published)

```sh
pip install colosseum
```

PyPI may lag GitHub releases; use **Releases** for offline tarballs and version-pinned wheels.

### Optional extras

| Capability | Install | Host / OS (not from pip) |
|------------|---------|---------------------------|
| Simulated bench / examples with `bench.sim.toml` | Default `colosseum` package | None beyond Python |
| VISA instruments | `pip install "colosseum[hardware]"` | IVI-compatible VISA (NI, Keysight, Tek, R&S, …) or `pyvisa-py`; see [platform notes](docs/sphinx/source/guides/platform_notes.rst) |
| Serial instruments (`driver = "serial"`) | `pip install "colosseum[hardware]"` | Correct `COM*` (Windows) or `/dev/ttyUSB*` (Linux); Linux: `dialout` or udev |
| SSH / remote shell (`col.shared`) | `pip install "colosseum[ssh]"` | Network reachability; keys/credentials in bench config |
| GUI runner (`colosseum --gui`) | `pip install "colosseum[gui]"` | Display; Linux: `python3-tk` |
| FT232H GPIO (`col.io.dio`) | `pip install "colosseum[io]"` | WinUSB/libusb as required; see [digital I/O](docs/sphinx/source/guides/io_digital.rst) |
| Spectrum trace plots | `pip install "colosseum[plot]"` | None |

Verify VISA after installing `colosseum[hardware]`: `python -m pyvisa info` inside your venv.

---

## Quickstart

With a simulated bench (no instruments):

```sh
colosseum run examples/test_power_rails.py --config examples/configs/bench.sim.toml
```

Each run writes `outputs/<timestamp>_<name>/` with `debug.log`, `execution.sqlite`, `summary.txt`, and `summary.json`.

**Suite example:**

```sh
colosseum run-suite tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml
```

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

More examples: [examples/](examples/).

---

## Documentation

| Topic | Location |
|-------|----------|
| User guides (install, config, RF, offline) | [docs/sphinx/source/guides/](docs/sphinx/source/guides/) |
| What is implemented today | [docs/scope.md](docs/scope.md) |
| Release assets and cut list | [docs/releasing.md](docs/releasing.md) |
| Developing this repository | [docs/DEVELOPING.md](docs/DEVELOPING.md) |

---

## License

MIT — see [LICENSE](LICENSE).
