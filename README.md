# Colosseum Core

[![CI](https://github.com/tps01/colosseum-core/actions/workflows/ci.yml/badge.svg?branch=develop&event=pull_request)](https://github.com/tps01/colosseum-core/actions/workflows/ci.yml?query=branch%3Adevelop)

## Documentation

During `colosseum run` and `colosseum run-suite`, Ctrl+C, POSIX `SIGTERM`,
and desktop Stop cancel the run with result `INCOMPLETE` and exit code `1`.
Cancellation skips pending suite slots, including scripted teardown. Active
script `finally` blocks and Core-managed resource cleanup can still run.
Saved results use the `-incomplete` directory suffix where applicable.
Forced termination or another interrupt during cleanup can leave partial artifacts.

HTML hub (GitHub Pages): <https://tps01.github.io/colosseum-core/>

First-party plugins publish API-reference Pages sites; they are linked from
that hub. See [docs/README.md](docs/README.md).

Core of the Colosseum test automation framework (hardware and software). It
provides:

- command, measurement, and verification decorators
- TOML configuration and plugin registration
- test and test suite runners
- SQLite database, logs, summaries, and artifacts
- optional desktop runner via the separate [`colosseum-extensions`](https://github.com/tps01/colosseum-extensions) package (`colosseum --gui` after install)

The GUI automation plugin (`colosseum-gui`) controls applications under test through `col.gui.*`.
Choose plugins by task in the [feature directory](https://tps01.github.io/colosseum-core/guides/first_party_plugins.html).

## Linked paths

Linked scripts follow the platform's Python behavior for sibling imports.
Colosseum looks for sibling config, metadata, and parameters beside the target script.
Relative entries in suite TOML files start beside the target TOML.
Core saves artifact references to their targets, using paths relative to the run
for artifacts inside it.

The cleanup script preserves symlinks and junctions and skips generated directories
that contain links. Executable ZIP bundles require regular files and directories.
Tar bundles can include relative symlinks whose targets are inside the bundle.

## Install

Download the wheel from [GitHub Releases](https://github.com/tps01/colosseum-core/releases)
and install it in a virtual environment. Replace `<version>` with
the downloaded filename. For development, use
`python -m pip install -r requirements.txt`.

```sh
python -m pip install "./colosseum_core-<version>-py3-none-any.whl"
```

## Develop

```sh
python -m venv .venv
python -m pip install -r requirements.txt
python scripts/run_tests.py
python scripts/run_static.py
python tests/regression/run_docgen_check.py --skip-pdf
```

See [docs/DEVELOPING.md](docs/DEVELOPING.md) for details.

For core-only parser fuzzing, see [the fuzz instructions](tests/fuzz/README.md).
