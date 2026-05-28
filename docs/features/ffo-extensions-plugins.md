# FFO: Extensions and Plugins

## Summary

Third-party and first-party packages extend Colosseum by registering namespaces, measurements, and verifications through the same entry-point mechanism. Extensions persist data via core database APIs and write artifacts into the active output directory.

## Actors

- Extension author
- Test engineer (consumer of `col.myext.*`)

## Preconditions

- Extension installed (`pip install colosseum-myext`)
- Entry point in group `colosseum.plugins`
- Core runtime active

## Main flow

1. User imports `colosseum`; accesses `col.web` (example).
2. Core lazy-loads plugins on namespace access or `col.plugins.load_all()`.
3. Extension `register(registry)` attaches namespace proxy, registers `ConfigSectionSpec` entries for repeatable TOML tables, and registers decorated functions.
4. User calls `col.vendor_x.measure_foo(...)`; decorators persist like core.
5. Extension creates optional SQLite tables `plugin_vendor_x_*`.

## Outputs

- Same evidence model as core
- Plugin tables in `execution.sqlite`
- Collision warnings per [ADR-009](../decisions/adr-009-plugin-namespace-collisions.md)

## Failure modes

| Condition | Behavior |
|-----------|----------|
| Plugin import error | WARNING; namespace unavailable |
| Namespace collision | WARNING; last-wins |
| Invalid plugin table name | Rejected by DatabaseManager |

## Exit code impact

Extension verifications participate in aggregation like first-party.

## Non-goals

- Sandboxed plugin execution
- Remote plugin install from cloud
- Config-declared plugin list (v1)

## Related design

- [ddd-plugin-registry.md](../design/ddd-plugin-registry.md)
- [ADR-002](../decisions/adr-002-plugin-registration.md), [ADR-009](../decisions/adr-009-plugin-namespace-collisions.md)
