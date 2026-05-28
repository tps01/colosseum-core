# FFO: Bench Configuration

## Summary

Users describe bench resources (instruments, SSH targets, timeouts) in TOML files. Colosseum loads, normalizes, and exposes configuration to core and plugins through a consistent access API.

## Actors

- Test engineer (maintains `bench.toml`)
- Extension code (reads equipment/shared sections)

## Preconditions

- Valid TOML file path
- Runtime initialized or `load_config` called before equipment/shared APIs (Wave 2+)

## Main flow

1. User calls `col.config.load_config("configs/bench.toml")` or passes `--config` to CLI.
2. Parser reads TOML (`tomli` on Python &lt; 3.11).
3. Loader normalizes single-table and array-of-table forms to internal lists (e.g. all `equipment.psu` entries as `[{psu_id: 1, ...}, ...]`).
4. Unknown keys log WARNING; missing required keys fail at first use with clear message ([ADR-003](../decisions/adr-003-config-validation.md)).
5. Plugins register repeatable config sections and ID fields at register time (not hard-coded in core); see [ddd-configuration.md](../design/ddd-configuration.md).
6. Extensions resolve `dmm_id`, `psu_id`, `ssh_id`, and project-specific IDs to connection parameters.
6. Logical instrument settings (voltage, OVP) remain in config; transport (`interface`, `resource`) separate from high-level API.

## Example shapes

**Single instrument:**

```toml
[equipment.dmm]
dmm_id = 1
driver = "visa"
resource = "USB0::0x1234::0x5678::INSTR"
```

**Multiple PSUs:**

```toml
[[equipment.psu]]
psu_id = 1
driver = "visa"
resource = "COM1"

[[equipment.psu]]
psu_id = 2
driver = "visa"
resource = "GPIB::5::INSTR"
```

**Interface vs model:**

```toml
[equipment.spectrum_analyzer]
sa_id = 1
model = "example-sa"
interface = "ethernet"
resource = "TCPIP0::192.168.1.25::INSTR"
timeout = 10.0
```

## Outputs

- In-memory config on runtime context
- Config path recorded in `run_metadata` and `debug.log` header

## Failure modes

| Condition | Behavior |
|-----------|----------|
| Missing file | ERROR, exit `1` |
| Invalid TOML | ERROR, exit `1` |
| Duplicate `psu_id` | ERROR at load |
| Unknown `dmm_id` at runtime | ERROR on API call |
| Unknown config key | WARNING only |

## Exit code impact

Load failures prevent test execution and yield exit `1` when invoked via CLI or explicit exit policy in script.

## Non-goals

- JSON Schema validation
- Environment variable substitution (post-MVP unless explicitly added)
- Encrypted secrets store
- Cloud-hosted config

## Related design

- [ddd-configuration.md](../design/ddd-configuration.md)
- [ADR-003](../decisions/adr-003-config-validation.md)
- [scope.md](../mvp/scope.md) Wave 1–2
