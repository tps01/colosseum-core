# User Documentation Inventory

This file tracks user-facing documentation for test engineers and plugin authors. Remaining work is polish, API reference completeness, and publication.

**Status legend:** `draft` | `usable` | `needs polish` | `missing`

## Sphinx Site

| Document | Audience | Status | Location / notes |
|----------|----------|--------|------------------|
| Installation | All users | usable | `docs/sphinx/source/guides/installation.rst` |
| Quickstart | All users | usable | `docs/sphinx/source/guides/quickstart.rst` |
| Configuration file syntax | Bench owners | usable | `docs/sphinx/source/guides/configuration.rst` (includes VSG/speca) |
| Digital I/O (col.io.dio) | Test engineers | usable | `docs/sphinx/source/guides/io_digital.rst` |
| RF equipment (VSG / speca) | Test engineers | usable | `docs/sphinx/source/guides/rf_equipment.rst` |
| Running test cases | Test engineers | usable | `docs/sphinx/source/guides/running_tests.rst` |
| Running suites | Test engineers | usable | `docs/sphinx/source/guides/running_suites.rst` |
| Output directory structure | All users | usable | `docs/sphinx/source/guides/output_artifacts.rst` (includes trace/capture artifacts) |
| Exit codes | CI authors | usable | `docs/sphinx/source/guides/exit_codes.rst` |
| Measurement and verification concepts | Test engineers | usable | `docs/sphinx/source/guides/measurements_verifications.rst` |
| Plugin development guide | Extension authors | usable | `docs/sphinx/source/guides/plugins.rst`; template scaffold `examples/plugins/colosseum_template/` (see README) |
| Host environment (col.host) | Test engineers | usable | `docs/sphinx/source/guides/host_environment.rst`; `examples/test_host_profile.py` |
| Windows / Linux notes | All users | usable | `docs/sphinx/source/guides/platform_notes.rst` |
| Equipment API reference | Test engineers | usable | Generated through `scripts/docgen`; docstrings on public `col.equipment.*` / `col.io.*` APIs |
| Shared utility API reference | Test engineers | draft | Generated through `scripts/docgen` |
| Multiprocessing guidance | Advanced users | missing | Deferred; recover design sketch from tag `doc-snapshot-pre-archive` per [archive/README.md](archive/README.md) |

## Source Of Truth For API Text

Function-level documentation should live in docstrings and generated API pages. Guides should explain workflows and link to generated API pages rather than duplicating detailed signatures.

Public `col.*` API docstrings and **`scripts/` maintainer entry points** use **Sphinx field lists** (`:param:`, `:type:`, `:returns:`, `:rtype:`, `:raises:`). Do not add Google-style `Args:` / `Returns:` / `Raises:` blocks.

Examples and guide snippets should keep one line per `col.*` call with keyword arguments inline, matching `examples/`.

## Current Gaps

- The Sphinx guides exist but are still lightweight in places (platform notes, multiprocessing).
- Generated API pages are supported by the docgen pipeline, but the root documentation set does not yet publish a versioned site.
- Per-function Sphinx-field docstrings are required on public `col.*` APIs and `scripts/` entry points; RF and lab instrument modules are covered; keep new APIs aligned with [`docs/api-naming-conventions.md`](api-naming-conventions.md).
- Equipment measurement keys must be unique per `(domain, command)` within domain `equipment` — documented in scope and the measurements guide.
- Multiprocessing remains intentionally deferred because parallel bench execution needs resource isolation design.

## Archived design reference (RF)

- [ddd-equipment-vsg-speca.md](archive/planning/design/ddd-equipment-vsg-speca.md) — historical API surface, models, artifacts, capability matrix
