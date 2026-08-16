# Colosseum Core

The small runtime at the center of Colosseum test automation. It provides:

- command, measurement, and verification decorators
- TOML configuration and plugin registration contracts
- single-test and suite runners
- SQLite evidence, logs, summaries, artifacts, and exit policy
- desktop GUI runner (customtkinter)
- modular documentation support

Bench protocols, device drivers, host inspection, SSH, and other integrations belong in
separately installed plugins.

## Install

```sh
pip install colosseum-core
```

Python 3.9+ is supported. For air-gapped hosts, use the parent integration checkout's
`offline/` wheelhouse tooling (build on a networked twin, install with `--no-index`).
Linux GUI needs Tk on the host image (`python3-tk` or a Tk-enabled Python)—it is not a
pip dependency.

Plugins expose namespaces such as `col.acme.*` through the `colosseum.plugins` entry-point
group. See the [plugin guide](docs/sphinx/source/guides/plugins.rst) and
[template package](examples/plugins/colosseum_template/).

## Develop

```sh
python -m venv .venv
python -m pip install -r requirements-dev.txt
python scripts/run_tests.py
python scripts/run_static.py
python tests/regression/run_docgen_check.py --skip-pdf
```

See [docs/DEVELOPING.md](docs/DEVELOPING.md) for details.
