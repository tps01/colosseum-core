# ADR-009: Plugin Namespace Collisions (v1)

> **Documentation note:** Normative behavior is in [mvp/scope.md](../mvp/scope.md), Sphinx user guides, and the codebase. Wave 1/2/3 references below are historical sequencing only.


## Status

Accepted

## Context

Architecture §6 leaves open whether namespace collisions fail immediately, warn, or require user selection.

## Decision

1. **v1 behavior: warn and last-wins.**
   - If two plugins register the same namespace (e.g. `equipment`), log WARNING with both plugin names.
   - Second registration replaces the namespace proxy on the registry.

2. **Load order:** Entry point discovery order (package metadata order) unless user calls `col.plugins.load_all(order=[...])` (explicit order API in registry, optional for MVP).

3. **Post-MVP:** Config option `plugin_policy = "fail" | "warn"` and explicit plugin ordering in TOML.

4. **Measurement/verification command names** are flat per domain in registry; duplicate registration logs warning; last registration wins for discovery doc only—runtime uses function actually called by user script.

## Consequences

- CI environments should monitor `debug.log` for collision warnings.
- Production benches should not rely on last-wins for safety-critical overrides.

## References

- [ddd-plugin-registry.md](../design/ddd-plugin-registry.md)
- [ffo-extensions-plugins.md](../features/ffo-extensions-plugins.md)
- Architecture §6, §22
