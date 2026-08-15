# Equipment API naming conventions

This document records intentional naming differences across `col.equipment.*` modules and
guides future harmonization without breaking existing scripts.

## Status

Naming is **stable** for the current release. New APIs should follow the preferred
columns below; existing parameters are not renamed in place without a deprecation period.

## Frequency parameters

| Style | Used by | Preferred for new APIs |
|-------|---------|------------------------|
| `frequency: float` (hertz) | `vsg`, `asg`, `speca` center | RF CW / center when unambiguous |
| `frequency_hz: float` | `vna`, `pwrmeter`, `rtsa`, `speca` span edges | Sweeps, spans, and RTSA/VNA |

Avoid mixing both names on the same instrument module.

## Center frequency helpers

| Name | Module |
|------|--------|
| `set_center_frequency` | `speca` |
| `set_center_freq` | `rtsa` |

Prefer `set_center_frequency` for new modules.

## Power / level parameters

| Name | Meaning |
|------|---------|
| `power_dbm` | RF output level (VSG, ASG) |
| `level_dbm` | Display reference level (`speca`) |
| `amplitude_dbm` | IQ playback level (`vsg.play_iq`) |
| `power` | DC load power in watts (`eload`, CP mode) |

## Verification kwargs

| Namespace | Expected value kwarg | Comparison |
|-----------|---------------------|------------|
| `col.equipment.*` tolerance verifiers | `expected_val` + `tolerance` | Absolute tolerance |
| `col.host.*` minimum verifiers | `minimum` | Lower bound |

## Output state measurements

`measure_output_state` on PSU/VSG returns `1.0` / `0.0` (float), not `bool`, so
tolerance verifiers can use `default_tolerance=0.0`.

## Offline / simulation drivers

| Mechanism | Config |
|-----------|--------|
| Colosseum cooperative sim | `driver = "sim"` |
| PyVISA-sim | `driver = "visa"` + `visa_backend = "sim"` |

Only `col.host.bench.verify_visa_available(allow_sim=...)` names simulation explicitly at the API layer.

## References

- Normative behavior: [`docs/scope.md`](scope.md), [`docs/sphinx/source/guides/measurements_verifications.rst`](sphinx/source/guides/measurements_verifications.rst)
- API text: Python docstrings (Sphinx autodoc / PDF user API)
