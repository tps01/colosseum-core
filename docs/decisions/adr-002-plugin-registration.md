# ADR-002: Plugin Registration

> **Documentation note:** Normative behavior is in [mvp/scope.md](../mvp/scope.md), Sphinx user guides, and the codebase. Wave 1/2/3 references below are historical sequencing only.


## Status

Accepted

## Context

Architecture §6 and open question §22 Q2 require third-party extensions to use the same pathway as first-party `equipment` and `shared`. Options: entry points, explicit import, config-declared plugins, or hybrid.

## Decision

1. **Primary mechanism: Python entry points** in group `colosseum.plugins`.

   Each entry point references a callable `register(registry)` that:
   - Registers a namespace name (e.g. `equipment`, `shared`, `web`)
   - Registers measurement and verification callables (for discovery/doc)
   - May register config schema hints (optional keys, required IDs)

2. **Lazy namespace attachment:** On first access to `col.<namespace>` or at explicit `col.plugins.load_all()`, the core loads entry points, invokes `register`, and caches the namespace proxy on the runtime context.

3. **First-party parity:** `colosseum-equipment` and `colosseum-shared` use the same entry point group; no special-case loader in core beyond default discovery order.

4. **Config-declared plugins (deferred):** v1 does not require listing plugins in TOML. Optional `plugins = ["my_pkg"]` may be added post-MVP for explicit ordering.

5. **Explicit import registration (escape hatch):** Test or project code may call `col.plugins.register_module(my_plugin)` for local development without packaging.

## Consequences

- `pyproject.toml` for each extension includes `[project.entry-points."colosseum.plugins"]`.
- Core implements `PluginRegistry` with ordered load and idempotent `register` calls.
- Namespace collision handling deferred to ADR-009.

## References

- [ddd-plugin-registry.md](../design/ddd-plugin-registry.md)
- [ffo-extensions-plugins.md](../features/ffo-extensions-plugins.md)
- Architecture §6
