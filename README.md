# Colosseum Core

Python test automation for embedded and bench system testing. Scripts use `import colosseum as col`, call measurement and verification APIs, and finish with **`col.endex()`** so logs, SQLite evidence, summaries, cleanup, and exit status are consistent.

**Distribution:** `colosseum-core` (this repository). First-party plugins are separate packages:

| Package | Provides |
|---------|----------|
| `colosseum-shared` | `col.shared.*` |
| `colosseum-host` | `col.host.*` |
| `colosseum-equipment` | `col.equipment.*`, `col.io.*` |

**Python:** 3.9+ (3.11 recommended for new Windows/Linux benches). **Status:** [implementation scope](docs/scope.md).

Contributing or working on the repository itself? See the [developer guide](docs/DEVELOPING.md).

---

## Install

```sh
pip install colosseum-core
pip install "colosseum-shared[ssh]" colosseum-host "colosseum-equipment[hardware]"
```

Or, once plugins are published:

```sh
pip install "colosseum-core[bench]"
```

| Capability | Install |
|------------|---------|
| Core + CLI + sim evidence | `colosseum-core` |
| VISA / serial instruments | `colosseum-equipment[hardware]` |
| SSH / remote shell | `colosseum-shared[ssh]` |
| Host profile checks | `colosseum-host` |
| GUI runner | `colosseum-core[gui]` |
| FT232H GPIO | `colosseum-equipment[io]` |
| Spectrum trace plots | `colosseum-equipment[plot]` |

## Quickstart

With a simulated bench (no instruments) and plugins installed:

```sh
colosseum run examples/test_power_rails.py --config examples/configs/bench.sim.toml
```

Each run writes `outputs/<timestamp>_<name>/` with `debug.log`, `execution.sqlite`, `summary.txt`, and `summary.json`.

**Suite example:**

```sh
colosseum run-suite tests/fixtures/suites/smoke.toml --config examples/configs/bench.sim.toml
```
