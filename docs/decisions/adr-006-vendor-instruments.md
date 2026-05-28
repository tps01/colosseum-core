# ADR-006: Vendor Instrument Minimum (DMM and PSU)

## Status

Accepted

## Context

Open question §22 Q6 and §14: first concrete instruments are Keysight EDU34450A DMM and TDK-Lambda Genesys PSU. MVP must balance time-to-bench with abstraction quality.

## Decision

1. **Wave 2 — Generic drivers:**
   - `col.equipment.dmm.measure_voltage` / `verify_voltage` use generic SCPI sequences documented in DDD D17
   - `col.equipment.psu.set_voltage`, `set_current_limit`, `set_output` use generic SCPI
   - Config: `driver = "visa"` (or serial where applicable), `model = "generic"` or omitted

2. **Wave 3 — Reference vendor implementations:**
   - `model = "keysight-edu34450a"` selects EDU34450A-specific command/parse paths
   - `model = "tdk-genesys"` selects Genesys-specific paths
   - Test scripts **do not** change between generic and vendor model when capability matches

3. **Manuals** are implementation references for D17, not public API contracts.

4. **Escape hatches** remain: `col.equipment.scpi.query`, `col.equipment.visa.*` for bespoke cases.

5. **Interface vs transport:** `interface` + `resource` in config select VISA resource string; high-level API unchanged (Architecture §8.5).

## Consequences

- Wave 2 benches can use any SCPI-compatible DMM/PSU with tuning via raw SCPI if needed.
- Wave 3 adds regression-tested reference models for project examples.

## References

- [ddd-equipment-dmm-psu.md](../design/ddd-equipment-dmm-psu.md)
- [ffo-laboratory-equipment.md](../features/ffo-laboratory-equipment.md)
- Architecture §14
