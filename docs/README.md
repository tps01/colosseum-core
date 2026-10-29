# Colosseum Documentation

This directory contains current project documentation. Historical planning notes
can be recovered from git history (see [archive/README.md](archive/README.md)).

## Start here

1. [Top-level README](../README.md) (users)
2. [Developer guide](DEVELOPING.md) (contributors; Sphinx PDF Part 2 is
   [runtime execution](sphinx/source/guides/runtime_execution.rst) and
   [plugin authoring](sphinx/source/guides/plugins.rst))
3. [Implementation scope and known gaps](scope.md)
4. [Sphinx manual](sphinx/README.md) (PDF primary; HTML backup)
5. [Testing and regression](testing/README.md)
6. [Cutting a release](releasing.md)
7. [Examples](../examples/)

Use [scope.md](scope.md), the user guides, and tests to establish intended
behavior, then compare the implementation. `scripts/docgen/build_all.py`
stages handwritten core guides. The standalone
`scripts/docgen/build_config_reference.py --output <file.rst>` inspects
plugins installed in its environment; that environment-specific output is
not currently included in the normal site or PDF. Core builds independently
of first-party plugins.

## Active documents

| Document | Description |
| --- | --- |
| [../README.md](../README.md) | User-facing overview, install, quickstart |
| [DEVELOPING.md](DEVELOPING.md) | Clone, editable install, tests, docgen, CI; Part 2 links to PDF Developing |
| [sphinx/source/guides/runtime_execution.rst](sphinx/source/guides/runtime_execution.rst) | Runtime execution (PDF Part 2) |
| [sphinx/source/guides/plugins.rst](sphinx/source/guides/plugins.rst) | Plugin authoring (PDF Part 2) |
| [sphinx/source/guides/glossary.rst](sphinx/source/guides/glossary.rst) | Glossary appendix |
| [scope.md](scope.md) | Implementation scope and known gaps |
| [sphinx/README.md](sphinx/README.md) | Sphinx/docgen build notes |
| [testing/README.md](testing/README.md) | Test tiers and profiling |
| [releasing.md](releasing.md) | Release workflow |
| [archive/README.md](archive/README.md) | Recover historical notes from Git |

## Example style

User-facing test scripts and guide snippets use one line per `col.*` call with
keyword arguments inline. See [examples/](../examples/).

## Public HTML hub

Browsed docs live on GitHub Pages:

- **Hub (this repo):** https://tps01.github.io/colosseum-core/
- **Plugins (separate sites):** equipment, gui, host, messaging, shared — each
  under `https://tps01.github.io/colosseum-<name>/`. Those sites lead with
  practical guides and configuration, followed by the autodoc API reference. Linked
  from the Sphinx landing page. The copy-out testware catalog is
  `colosseum-library` (GitHub); the hub documents it under
  **Testware library** (`guides/testware_library`).

There is no separate umbrella `tps01/colosseum` docs repo.

## CI documentation outputs

- The Sphinx **PDF** is the primary manual (release builds it; CI uploads the
  PDF artifact when `latexmk` is available).
- HTML is a backup of the same sources and is what GitHub Pages deploys.
- The Documentation workflow (`.github/workflows/docs.yml`) builds HTML and
  deploys Pages on `workflow_dispatch` and on pushes that touch docs sources.

## Documentation standards

See the [October 2026 review remediation](documentation-review-2026-10.md)
for the cross-package changes, verified behavior, and validation limits.

Lead with the task and its observable result. Define evidence keys and failure
conditions before implementation details. Keep release history out of current
overviews. Public callables document every argument, units, defaults, return
values, relevant exceptions, and driver/platform limits. Do not claim hardware
qualification based on simulated or mocked tests.

Examples specify prerequisites, file layout, the working directory, exact
invocation, and expected results. Identify simulation and literal recording
demonstrations. Stateful hardware examples use local `try/finally` cleanup.
Link workflows to configuration, related APIs, and the core evidence guide.

Build each site with warnings treated as errors. Run simulated examples and
check links before publishing. Plugin Pages builders own their navigation;
edit source guides and docstrings rather than generated `build/` files.
