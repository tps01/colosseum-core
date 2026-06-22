# colosseum_template

Copy-ready stub for a **third-party Colosseum extension**. Fork this directory, follow [RENAME.md](RENAME.md), and implement your bench-specific API under your own namespace (default demo namespace: `template` → `col.template.*`).

For deeper background see the Colosseum plugin guide: [`docs/sphinx/source/guides/plugins.rst`](../../../docs/sphinx/source/guides/plugins.rst) (in the Colosseum repo).

---

## Part A — Extension author: build your package

### 1. Copy and rename

Copy `examples/plugins/colosseum_template/` to your own repository or folder. Work through [RENAME.md](RENAME.md): replace `colosseum_template`, `colosseum-template`, and `template` with your package name, distribution name, and namespace.

### 2. Implement the API

Edit `colosseum_template/api.py` (rename the package directory when forking):

- Use `@command` for setup/actions, `@measurement` for evidence, `@verification` for checks (import from `colosseum.decorators`).
- Set `MeasurementSource(domain="template", ...)` to match your namespace (change `"template"` when forking).
- In test and example scripts use **one keyword argument per `col.*` call** on a single line (Colosseum project style).
- Replace `# TODO: Your code here` stubs with real logic.

Optional helpers:

- `connections.py` — config lookup and cached instrument handles (see `colosseum_equipment/connections.py` in the Colosseum repo).
- `validators.py` — custom config warnings; register in `__init__.py`.

### 3. Wire `register(registry)`

In `colosseum_template/__init__.py`:

- **Required:** `registry.register_namespace("template", api)` — exposes `col.template.*` after install.
- **Required:** `registry.register_config_section(ConfigSectionSpec(...))` with `dotted_path`, `id_field`, `required_keys`, and optional `optional_keys`.
- **Optional:** `registry.register_config_validator("template.device", fn)` — returns warning strings.
- **Optional:** `registry.register_shutdown(callable)` — release hardware on `col.endex()`.

Keep imports inside `register()` like first-party plugins.

### 4. Declare entry points

In `pyproject.toml`:

```toml
[project.entry-points."colosseum.plugins"]
template = "colosseum_template:register"

[project.entry-points."colosseum.docgen"]
template = "colosseum_template.docgen_entry:spec"
```

The entry-point **key** is metadata; the runtime namespace is the string passed to `register_namespace`. Docgen entry points are optional.

Pin `colosseum` in `dependencies` when you publish (e.g. `colosseum>=0.13.12`).

### 5. Add bench config

Add repeatable TOML sections using array-of-tables syntax. Each row needs the section's integer `id_field`:

```toml
[[template.device]]
device_id = 1
serial = "TEMPLATE-001"
```

See `configs/bench.template.toml`. Merge sections into your project's bench file. Unknown keys produce **warnings**; missing **required** keys raise errors when config is loaded.

### 6. Install locally (editable)

From this extension root:

```powershell
pip install -e .
```

**Third-party extensions require install** so setuptools registers `colosseum.plugins` entry points. Running from a bare checkout without `pip install -e .` will not load your plugin (built-in `equipment` / `shared` / `host` still work via Colosseum's monorepo fallback).

You also need Colosseum installed (`pip install colosseum` or `pip install -e .` from the Colosseum repo).

### 7. Verify

```powershell
python examples/smoke_test.py
```

Or:

```powershell
colosseum run examples/smoke_test.py --config configs/bench.template.toml
```

Quick import check (after `load_config`):

```powershell
python -c "import colosseum as col; col.config.load_config('configs/bench.template.toml'); print(col.template)"
```

Requires Colosseum **>= 0.13.12** for dynamic `col.<namespace>` on third-party plugins.

### 8. Optional docgen

Fill in `docgen_entry.py` (`DocgenModuleSpec`). When Colosseum docgen is available:

```powershell
python scripts/docgen/build_module.py
```

### 9. Optional tests

This stub does **not** ship tests. Add your own `tests/` directory when ready. Patterns:

- Unit: API and verifiers with `unit_runtime_context` (see Colosseum `tests/unit/`).
- Integration: `ensure_plugins_loaded()` and assert your namespace is registered (see `tests/integration/test_plugin_registry_load.py`).

### 10. Publishing

Build wheels with `python -m build`. Distribute via your package index or internal wheel share. Do not register namespaces that collide with built-ins: `equipment`, `shared`, `io`, `host`.

---

## Part B — End user: install and use on a bench

### 1. Prerequisites

- Python >= 3.9
- Colosseum installed (`pip install colosseum` or your organization's offline bundle)
- Any optional extras your extension documents (e.g. `colosseum[hardware]` for VISA)
- Colosseum **>= 0.13.12** if the extension uses `col.yournamespace.*` without pre-declared proxies

### 2. Install the extension

From a release wheel:

```powershell
pip install acme-bench==1.0.0
```

For lab development:

```powershell
pip install -e C:\path\to\acme_bench
```

The extension must be installed in the **same Python environment** as Colosseum and your test scripts.

### 3. Bench TOML

Add the extension's section(s) to your project bench file. Example (replace `template` with your namespace after the author renames):

```toml
[[template.device]]
device_id = 1
serial = "LAB-DUT-001"
```

### 4. Use in test scripts

```python
import colosseum as col

col.config.load_config("bench.toml")
col.template.measure_widget_count(device_id=1, key="widgets")
col.template.verify_widget_count(key="widgets", expected_val=10.0, tolerance=0.0)
col.endex()
```

- **`col.endex()`** — flush logs/DB, write summaries, exit `0`/`1` for test runs.
- **Utility scripts** — `col.config.load_config("bench.toml", no_artifacts=True)` or CLI `--no-artifacts` to skip `outputs/` (see Colosseum running-tests guide).

### 5. Use via CLI

```powershell
colosseum run my_test.py --config bench.toml
```

The extension must be installed; the CLI loads plugins before running `main()`.

### 6. Evidence

Normal runs create `outputs/<timestamp>_<name>/` with `debug.log`, `execution.sqlite`, `summary.txt`, and `summary.json`. Use `--no-artifacts` or `no_artifacts=True` when you only need equipment control without persisted evidence.

### 7. Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `Namespace '…' is not registered` | Extension not installed (`pip install -e .` / wheel missing) |
| `Configuration is not loaded` | Call `col.config.load_config(path)` before API calls |
| Missing required keys | Bench TOML row incomplete for your `ConfigSectionSpec` |
| `Config section … is already registered` | Two plugins registered the same section; rename or remove duplicate |
| `AttributeError: …` on `col.yournamespace` | Old Colosseum (< 0.13.12) or typo in namespace |

---

## Layout

```
colosseum_template/
  pyproject.toml
  README.md
  RENAME.md
  configs/bench.template.toml
  examples/smoke_test.py
  colosseum_template/
    __init__.py       # register(registry)
    api.py            # col.template.*
    connections.py    # TODO stubs
    validators.py     # TODO stubs
    docgen_entry.py   # optional DocgenModuleSpec
```
