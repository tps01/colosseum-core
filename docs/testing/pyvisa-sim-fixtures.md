# PyVISA-sim fixtures for Colosseum

Colosseum supports two offline instrument simulation layers:

| Layer | Bench config | Use |
|-------|----------------|-----|
| **Colosseum `SimTransport`** | `driver = "sim"` ([`examples/configs/bench.sim.toml`](../../examples/configs/bench.sim.toml)) | Fast CI/e2e; cooperative multi-instrument behavior (e.g. DMM reads PSU 1). |
| **PyVISA-sim** | `driver = "visa"`, `visa_backend = "sim"`, `sim_definition = "..."` | SCPI fidelity from YAML; per-instrument definitions. |

## Install

PyVISA-sim is included in the default Colosseum install. Requires **Python 3.10+** (`pyvisa-sim` 0.7.x).

## Run tests

```bash
pytest -m visa_sim -q
```

CI runs this marker on Python 3.10+ (see [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)).

## Fixture layout

```
tests/fixtures/pyvisa_sim/
  generic_psu.yaml
  generic_dmm.yaml
  keysight_edu34450a.yaml
  tdk_genesys.yaml
  keysight_esg.yaml
  keysight_e4407b_sa.yaml
  tektronix_rsa5100b_sa.yaml
```

Example bench files: [`examples/configs/bench.visa-sim.toml`](../../examples/configs/bench.visa-sim.toml), [`examples/configs/bench.rf.visa-sim.toml`](../../examples/configs/bench.rf.visa-sim.toml).

The `resource` string in TOML must match a key under `resources:` in the YAML (PyVISA normalizes addresses, e.g. `GPIB::1::INSTR` → `GPIB0::1::INSTR`).

## Authoring YAML from manuals

1. List SCPI strings emitted by the Colosseum driver ([`colosseum_equipment/instruments/`](../../colosseum_equipment/instruments/)).
2. Create a [PyVISA-sim definition file](https://pyvisa-sim.readthedocs.io/en/latest/definitions.html) with:
   - `eom` terminators (`\n` matches Colosseum’s visa-sim transport),
   - `dialogues` for `*IDN?` and fixed responses,
   - `properties` with `getter`/`setter` pairs for stateful commands (use `specs: type: float` for numeric state).
3. Map `resources:` to bench `resource` values.
4. Run `pytest -m visa_sim` and adjust command strings until queries pass.

Reference workflow: [QCoDeS simulated PyVISA instruments](https://microsoft.github.io/Qcodes/examples/writing_drivers/Creating-Simulated-PyVISA-Instruments.html).

## Limitations

- PyVISA-sim models **separate** devices; coupled bench behavior (DMM following PSU output) remains on `driver = "sim"`.
- Simulators validate command/response shape, not timing, acquisition depth, or overlapping commands.

## New vendor models

Provide programmer-manual SCPI tables and `*IDN?` strings before adding YAML and `model = "..."` factory entries. Hardware sign-off uses [regression-test-procedure.md](regression-test-procedure.md) with [`configs/bench.local.toml.example`](../../configs/bench.local.toml.example).
