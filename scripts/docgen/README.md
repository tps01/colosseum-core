# Colosseum modular documentation generation

Documentation is built in three stages so **core**, **first-party plugins**, and **third-party extensions** use the same tooling.

## Pipeline

```text
colosseum.docgen entry points
        │
        ▼
  build_module.py  ──►  build/docgen/<module_id>/rst/ + manifest.json
        │                    (one run per package)
        ▼
    stitch.py      ──►  build/docgen/site/source/  (+ docs/sphinx/source guides)
        │
        ▼
  sphinx-build     ──►  build/docgen/site/html/
```

## Commands

From the repository root (with ``pip install -e ".[docs]"``):

```bash
# Full site
python scripts/docgen/build_all.py

# One module only
python scripts/docgen/build_module.py --module-id colosseum
python scripts/docgen/build_module.py --module-id colosseum_equipment

# Stitch only (after modular runs)
python scripts/docgen/stitch.py

# RST source without HTML
python scripts/docgen/build_all.py --skip-html
```

HTML output: `build/docgen/site/html/index.html`

Remove generated files: `python scripts/cleanup.py` (use `--dry-run` first).

## Third-party extension contract

1. Implement runtime registration (``colosseum.plugins``) as today.
2. Add ``docgen_entry.py`` with a ``spec()`` function:

```python
from colosseum.docgen_spec import DocgenModuleSpec

def spec():
    return DocgenModuleSpec(
        module_id="myvendor_bench",
        title="My Vendor Bench",
        import_packages=["myvendor_bench"],
        autodoc_modules=["myvendor_bench"],
        order=50,
        namespace="myvendor",
    )
```

3. Register the entry point in ``pyproject.toml``:

```toml
[project.entry-points."colosseum.docgen"]
myvendor = "myvendor_bench.docgen_entry:spec"
```

4. Install the package, then run ``build_all.py`` (or ``build_module.py --module-id myvendor_bench``).

No changes to Colosseum scripts are required when the entry point is present.

## User guides

Hand-written RST lives in ``docs/sphinx/source/guides/``. The stitch step copies them into the site source tree; API reference comes from autodoc staging.

After ``sphinx-apidoc``, ``build_module.py`` patches ``colosseum.decorators.rst`` with
``:exclude-members: measurement, verification`` so package re-exports do not duplicate
submodule doc targets (``colosseum.decorators.measurement`` module vs function name).

## Entry point group

| Group | Purpose |
|-------|---------|
| ``colosseum.docgen`` | Returns :class:`~colosseum.docgen_spec.DocgenModuleSpec` per installable unit |
| ``colosseum.plugins`` | Runtime plugin registration (separate) |

Built-in monorepo packages are discovered via ``colosseum.docgen`` entry points in ``pyproject.toml``, with a source-tree fallback when metadata is not installed.
