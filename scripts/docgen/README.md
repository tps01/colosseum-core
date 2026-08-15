# Documentation generation

Build standalone core HTML documentation:

```sh
python scripts/docgen/build_all.py --skip-pdf
```

The full build additionally requires `latexmk`:

```sh
python scripts/docgen/build_all.py
```

The pipeline discovers installed `colosseum.docgen` entry points, stages each
`DocgenModuleSpec`, generates the plugin configuration reference, stitches guides, and
invokes Sphinx. A core-only environment documents only core.

Useful phase commands:

```sh
python scripts/docgen/build_all.py --stage-only
python scripts/docgen/build_all.py --html-only
python scripts/docgen/build_all.py --pdf-only
```

Plugins own their API docs and may join an aggregate build by publishing a
`colosseum.docgen` entry point.
