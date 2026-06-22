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
build_config_reference.py ──► build/docgen/config_reference.rst
        │                    (from plugin ConfigSectionSpec; SSOT for bench keys)
        ▼
    build_user_api.py ──► build/docgen/user_api/rst/  (commands, measurements, verifications)
        │
        ▼
    stitch.py      ──►  build/docgen/site/source/  (+ docs/sphinx/source guides)
        │
        ├─► sphinx-build -b html (index.rst)  ──► build/docgen/site/html/
        └─► sphinx-build -b latex (index_pdf.rst) + latexmk ──► build/docgen/site/latex/colosseum.pdf
```

## Commands

From the repository root (with ``pip install -e ".[docs]"``):

```bash
# Full site (HTML + PDF; requires latexmk and a LaTeX distribution)
python scripts/docgen/build_all.py

# HTML only (no LaTeX)
python scripts/docgen/build_all.py --skip-pdf

# PDF only (after staging)
python scripts/docgen/build_all.py --skip-html

# One module only
python scripts/docgen/build_module.py --module-id colosseum
python scripts/docgen/build_module.py --module-id colosseum_equipment

# Bench config reference only (from registered plugins)
python scripts/docgen/build_config_reference.py

# Stitch only (after modular runs + config reference)
python scripts/docgen/stitch.py
```

Outputs:

- HTML: `build/docgen/site/html/index.html` (full guides + developer API reference)
- PDF: `build/docgen/site/latex/colosseum.pdf` (run-the-bench guides + filtered user API only)

**LaTeX prerequisites (default build):** `latexmk` on `PATH`, plus a TeX distribution (Ubuntu: `latexmk texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra`; Windows: MiKTeX or TeX Live).

Remove generated files: `python scripts/cleanup.py` (use `--dry-run` first).

## Third-party extension contract

1. Implement runtime registration (``colosseum.plugins``) as today.
2. Add ``docgen_entry.py`` with a ``spec()`` function:

```python
from colosseum.docgen_spec import DocgenModuleSpec

def spec():
    return DocgenModuleSpec(
        module_id="colosseum_template",
        title="Colosseum Template Extension",
        import_packages=["colosseum_template"],
        autodoc_modules=["colosseum_template"],
        order=50,
        namespace="template",
    )
```

3. Register the entry point in ``pyproject.toml``:

```toml
[project.entry-points."colosseum.docgen"]
template = "colosseum_template.docgen_entry:spec"
```

4. Install the package, then run ``build_all.py`` (or ``build_module.py --module-id colosseum_template``).

No changes to Colosseum scripts are required when the entry point is present.

## User guides

Hand-written RST lives in ``docs/sphinx/source/guides/``. The stitch step copies them into the site source tree; API reference comes from autodoc staging.

After ``sphinx-apidoc``, ``build_module.py`` patches ``colosseum.decorators.rst`` with
``:exclude-members: command, measurement, verification`` so package re-exports do not duplicate
submodule doc targets (``colosseum.decorators.measurement`` module vs function name).

## Entry point group

| Group | Purpose |
|-------|---------|
| ``colosseum.docgen`` | Returns :class:`~colosseum.docgen_spec.DocgenModuleSpec` per installable unit |
| ``colosseum.plugins`` | Runtime plugin registration (separate) |

Built-in monorepo packages are discovered via ``colosseum.docgen`` entry points in ``pyproject.toml``, with a source-tree fallback when metadata is not installed.
