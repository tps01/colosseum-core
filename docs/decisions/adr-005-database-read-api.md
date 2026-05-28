# ADR-005: Database Read API Shape

## Status

Accepted

## Context

Open question §22 Q5: what should public read helpers return? Users need inspection without raw SQL; core should avoid heavy dependencies.

## Decision

1. **Return type:** Immutable **dataclasses** (or `typing.NamedTuple`) for `MeasurementRecord`, `VerificationRecord`, `RunMetadataRecord`, `EventRecord`, `ArtifactRecord`.

2. **Collection API:** Functions return `List[...]` (empty list if no rows). No pandas dependency.

3. **Public functions (Wave 3):**
   - `col.database.read_measurements() -> List[MeasurementRecord]`
   - `col.database.read_verifications() -> List[VerificationRecord]`
   - `col.database.read_run_metadata() -> List[RunMetadataRecord]`
   - `col.database.read_table(name: str) -> List[dict]` — escape hatch for plugin tables; values as JSON-deserialized dicts where applicable

4. **JSON fields:** `value_json`, `expected_json`, `actual_json` exposed as parsed Python objects on records.

5. **Schema stability:** v1 does not guarantee column-level stability for direct SQL; read helpers are the compatibility boundary.

6. **During run:** Read helpers require active runtime or explicit path to `execution.sqlite` (post-run: optional path argument in v1.1; MVP: active context only).

## Consequences

- Core defines record types in `colosseum.database.records`.
- Sphinx documents field meanings on dataclasses.

## References

- [ddd-database.md](../design/ddd-database.md)
- [ddd-database-read-api.md](../design/ddd-database-read-api.md)
- Architecture §11
