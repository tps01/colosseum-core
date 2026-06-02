# FFO: Laboratory Equipment Control

> **Documentation note:** Normative behavior is in [mvp/scope.md](../mvp/scope.md), Sphinx user guides, and the codebase. Wave 1/2/3 references below are historical sequencing only.


## Summary

Users control bench instruments (PSU, DMM, VSG, spectrum analyzer, serial devices) through high-level Colosseum APIs. Transport (VISA, serial) and protocol (SCPI) are configuration concerns; tests use stable `col.equipment.*` calls with optional raw escape hatches.

## Actors

- Test engineer
- Equipment plugin maintainer

## Preconditions

- `colosseum-equipment` installed
- Bench config defines instruments with `*_id`, `resource`, optional `driver` (defaults to `visa`), `model`, `interface`
- Runtime and config loaded

## Main flow

1. User configures PSU/DMM/VSG/speca in TOML ([ffo-bench-configuration.md](ffo-bench-configuration.md)).
2. User enables output: `col.equipment.psu.set_output(psu_id=1, enabled=True)`.
3. User measures: `col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")`.
4. User verifies: `col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)`.
5. RF example: set VSG CW, sweep speca, peak search, save trace CSV ([rf_equipment.rst](../sphinx/source/guides/rf_equipment.rst)).
6. For custom cases: `col.equipment.scpi.query(...)` or serial read/write APIs (`vsg_id=` / `speca_id=` supported).

## Wave breakdown

| Capability | Wave |
|------------|------|
| VISA transport, SCPI helpers, serial | 2 |
| Generic DMM/PSU | 2 |
| Keysight EDU34450A, TDK-Lambda Genesys | 3 ([ADR-006](../decisions/adr-006-vendor-instruments.md)) |
| Generic VSG/speca, trace artifacts | RF Wave A |
| Vector arb upload, RTSA capture, vendor ESG/E4407B/RSA5100B | RF Wave B |

## Outputs

- Measurement/verification rows in SQLite
- Optional artifact files (spectrum traces, IQ captures, screenshots)

## Failure modes

| Condition | Result |
|-----------|--------|
| VISA connection failure | ERROR on measurement |
| SCPI error response | ERROR with instrument message in log |
| Out-of-range verify | FAIL |
| Unsupported driver capability | `EquipmentCapabilityError` |

## Exit code impact

Via required verifications on equipment measurements.

## Non-goals

- Every vendor instrument library
- CAN/JTAG/DAQ in MVP (architecture mentions future)
- Automatic instrument discovery (VISA scan) in v1

## Related design

- [ddd-equipment-architecture.md](../design/ddd-equipment-architecture.md)
- [ddd-equipment-dmm-psu.md](../design/ddd-equipment-dmm-psu.md)
- [ddd-equipment-vsg-speca.md](../design/ddd-equipment-vsg-speca.md)
