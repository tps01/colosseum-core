# Sphinx user documentation

Hand-written guides: `source/guides/`

Build the full site from the repository root:

```bash
pip install -e .
pip install -r requirements-dev.txt
python scripts/docgen/build_all.py
```

Open `build/docgen/site/html/index.html`.

See [scripts/docgen/README.md](../../scripts/docgen/README.md) for the modular pipeline and third-party extension contract.
