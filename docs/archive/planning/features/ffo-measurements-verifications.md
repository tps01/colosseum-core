# FFO: Measurements and Verifications

> **Archived planning document.** For current behavior see [scope.md](../../../scope.md), Sphinx user guides, examples, and the codebase. Wave references below are historical only.


## Summary

Measurements collect evidence from equipment, the DUT, or host utilities and persist results. Verifications compare evidence to expectations. Both use framework decorators for logging, timing, persistence, and aggregation.

## Actors

- Test engineer (calls `col.*` APIs)
- Plugin author (registers `@measurement` / `@verification` functions)

## Preconditions

- Active runtime context
- For verifications: prior measurement with matching `key` (unless verification handles missing data as ERROR)
- Output directory allocated when persistence occurs

## Main flow — measurement

1. User calls e.g. `col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")`.
2. Decorator logs start, records timestamp.
3. Implementation interacts with resource, obtains value (and optional artifact path).
4. Row inserted into `measurements` table (`domain`, `command`, `key`, `value_json`, `units`, `status`, ...).
5. Python return value passed to caller (e.g. `float` voltage).

## Main flow — verification

1. User calls e.g. `col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)`.
2. Decorator loads evidence from the **measurement command(s) declared on that verification API** (e.g. `verify_voltage` reads `measure_voltage`, not `verify_voltage`).
3. Compare actual vs expected; set status PASS/FAIL; on missing data set ERROR.
4. Row inserted into `verifications` table.
5. Result object returned (status, message).

## Key semantics

- Same `key` allowed across **different** domains/commands (e.g. DMM vs SSH).
- Duplicate `key` for the **same** measurement command: rejected unless command is registered with multi-row support (`row_index` discriminator); see [ddd-database.md](../design/ddd-database.md).
- Large traces: prefer artifact file + pointer in `artifact_path`; multi-row per key only when documented for that command (architecture §11.2).

## Optional verifications

```python
col.equipment.dmm.verify_voltage(key="engineering_probe_point", expected_val=1.8, tolerance=0.1, optional=True)
```

- Stored and logged with `optional=true` in DB
- FAIL/ERROR do not affect overall pass or exit code
- Still appear in summaries (Wave 3)

## Result states

| State | Meaning |
|-------|---------|
| PASS | Check completed; expectation met |
| FAIL | Check completed; expectation not met |
| ERROR | Check could not complete (missing data, exception, equipment fault) |
| SKIP | Intentionally skipped step |

Aggregation: overall PASS iff no required verification has FAIL or ERROR ([ddd-results-exit-codes.md](../design/ddd-results-exit-codes.md)).

## Failure modes

| Condition | Result |
|-----------|--------|
| Measurement hardware timeout | measurement status ERROR or exception → verification ERROR |
| Missing key for verify | ERROR |
| Malformed stored JSON | ERROR |
| User exception in decorated function | ERROR, logged with stack |

## Exit code impact

Required verification FAIL or ERROR → exit `1`. Optional failures excluded.

## Non-goals

- Automatic retry of measurements
- Requirement traceability IDs
- Built-in statistical tolerance types beyond per-API parameters (extensions may add)

## Related design

- [ddd-measurement-verification.md](../design/ddd-measurement-verification.md)
- [ddd-database.md](../design/ddd-database.md)
- [ddd-results-exit-codes.md](../design/ddd-results-exit-codes.md)
