# User-Facing Documentation Tracker

Architecture §19 defines documentation Colosseum should provide to **test engineers and plugin authors**. This tracker records those deliverables separately from FFOs/DDDs (implementation planning).

**Status legend:** `planned` | `draft` | `done`

## Sphinx site (post–Wave 1 foundation)

| Document | Audience | Target | Status | Notes |
|----------|----------|--------|--------|-------|
| Installation | All users | Wave 1 complete | draft | `docs/sphinx/source/guides/installation.rst` |
| Quickstart | All users | Wave 1 complete | draft | `docs/sphinx/source/guides/quickstart.rst` |
| Configuration file syntax | Bench owners | Wave 2 | draft | `docs/sphinx/source/guides/configuration.rst` |
| Running test cases | Test engineers | Wave 1 complete | draft | `docs/sphinx/source/guides/running_tests.rst` |
| Running suites | Test engineers | Wave 3 | draft | `docs/sphinx/source/guides/running_suites.rst` |
| Output directory structure | All users | Wave 1–3 | draft | `docs/sphinx/source/guides/output_artifacts.rst` |
| Exit codes | CI authors | Wave 1 complete | draft | `docs/sphinx/source/guides/exit_codes.rst` |
| Measurement & verification concepts | Test engineers | Wave 1 complete | draft | `docs/sphinx/source/guides/measurements_verifications.rst` |
| Equipment API reference | Test engineers | Wave 2 | draft | Autodoc via `scripts/docgen` |
| Shared utility API reference | Test engineers | Wave 2 | draft | Autodoc via `scripts/docgen` |
| Plugin development guide | Extension authors | Wave 2 | draft | `docs/sphinx/source/guides/plugins.rst` |
| Windows / Linux notes | All users | Wave 2 | draft | `docs/sphinx/source/guides/platform_notes.rst` |
| Multiprocessing guidance | Advanced users | Post-MVP | planned | Link to [ddd-multiprocessing.md](../design/ddd-multiprocessing.md) |

## Source of truth for API text

Function-level documentation lives in **docstrings** (Sphinx autodoc). User guides link to generated API pages; avoid duplicating signatures in prose guides.

**Example style:** Quickstart and other user guides should show test scripts with one line per `col.*` invocation (keyword args inline), matching [examples/](../../examples/).

## Relationship to current docs

| Doc type | Purpose |
|----------|---------|
| FFO / DDD / ADR | Build the framework correctly |
| User guides (this tracker) | Teach users how to operate the framework |

## When to start

- **Wave 1:** Installation, quickstart, running tests, exit codes, output basics (minimal RST in `docs/sphinx/`).
- **Wave 2:** Config syntax, equipment/shared API, plugin guide, platform notes.
- **Wave 3:** Suites, `summary.txt`, database read helpers for advanced users.
