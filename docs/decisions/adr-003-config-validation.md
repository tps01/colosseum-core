# ADR-003: Configuration Validation (v1)

> **Documentation note:** Normative behavior is in [mvp/scope.md](../mvp/scope.md), Sphinx user guides, and the codebase. Wave 1/2/3 references below are historical sequencing only.


## Status

Accepted

## Context

Open question §22 Q3: how strict should v1 configuration validation be? Users need flexible TOML; extensions need predictable access patterns.

## Decision

1. **Always validate:**
   - File exists and parses as TOML
   - Duplicate `*_id` values within the same equipment type after normalization are rejected with a clear error
   - Referenced `*_id` in test/API calls must exist after normalization (checked at use time if not at load time)

2. **Structural normalization (required):**
   - Single table `[equipment.dmm]` and array form `[[equipment.dmm]]` normalize to a list of dicts internally
   - Access pattern: `config.get_equipment("dmm", dmm_id=1)` regardless of TOML shape

3. **Extension validation (lightweight):**
   - Plugins register `ConfigSectionSpec` (dotted path, id field, required keys) for repeatable TOML tables — core does not hard-code only `equipment` / `shared`
   - Each plugin may register `validate_section` hooks per dotted path
   - Missing required keys → ERROR at first connection/use with message naming section and id
   - Unknown keys in a section → **warning** in `debug.log`, not failure

4. **No JSON Schema / full schema validation in v1.**

5. **Defaults:** Extensions apply safe defaults (timeouts, etc.) when keys omitted; defaults documented in extension docstrings.

## Consequences

- Config loader in core is TOML-centric, not schema-centric.
- Post-MVP: optional strict mode or JSON Schema for CI.

## References

- [ddd-configuration.md](../design/ddd-configuration.md)
- [ffo-bench-configuration.md](../features/ffo-bench-configuration.md)
- Architecture §8
