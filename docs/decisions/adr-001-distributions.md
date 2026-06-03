# ADR-001: Distribution and Namespace Model

> **Documentation note:** Normative behavior is in [mvp/scope.md](../mvp/scope.md), Sphinx user guides, and the codebase. Wave 1/2/3 references below are historical sequencing only.


## Status

Accepted

## Context

Architecture §5 and open question §22 Q1 ask how Colosseum is packaged and what users import. The framework must keep core dependencies minimal while allowing optional hardware and protocol stacks.

## Decision

1. **Three first-party distributions:**
   - `colosseum` — core runtime, config, runner, database, logging, decorators, plugin loader
   - `colosseum-equipment` — bench equipment adapters (`col.equipment`)
   - `colosseum-shared` — cross-domain utilities (`col.shared`)

2. **Single user import:** `import colosseum as col` (recommended in examples and docs).

3. **Core owns the top-level namespace.** Extensions attach submodules on the active runtime (e.g. `col.equipment`, `col.shared`) via the plugin mechanism; they are not separate user-facing import roots.

4. **Extension packages use underscored Python module names** (`colosseum_equipment`, `colosseum_shared`) while registering user-facing namespaces under `col`.

5. **Optional install:** Users may install only `colosseum` for development of custom plugins; equipment and shared are recommended defaults for bench testing.

## Consequences

- PyPI/release pipelines publish three wheels (or one meta-package later if desired; not MVP).
- Versioning: core and extensions should declare compatible version ranges in extension metadata.
- Documentation and examples always use `col.*`, never `from colosseum_equipment import ...` for test scripts.

## References

- [scope.md](../mvp/scope.md)
- [ddd-core-package-layout.md](../design/ddd-core-package-layout.md)
- Architecture §5, §20

## Addendum (0.3.0)

The repository ships **one** setuptools project (`colosseum`) containing `colosseum`, `colosseum_equipment`, and `colosseum_shared`. Runtime dependencies (VISA, serial, SSH, GUI) are installed by default; PyVISA-sim is test-only (`.[test]` extra). Split PyPI distributions remain deferred. Dev tools use `requirements-dev.txt` or optional extras `test`, `docs`, and `mutation`.
