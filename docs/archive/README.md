# Historical documentation archive

Normative documentation for Colosseum is:

- [docs/mvp/scope.md](../mvp/scope.md) — implemented behavior
- [docs/sphinx/source/guides/](../sphinx/source/guides/) — user guides (built by docgen)
- [examples/configs/](../../examples/configs/) — bench TOML patterns
- Runtime code and generated bench config reference (`python scripts/docgen/build_all.py`)

## Recovering removed files

Some pre-MVP and deferred design files were **removed from the git tree** to reduce drift.
They are not in a normal clone. Recover them from the snapshot tag:

```bash
git fetch --tags
git tag -l doc-snapshot-pre-archive
git show doc-snapshot-pre-archive:scratchpad/colosseum_architecture_document.md
```

To copy all listed paths into this directory locally (gitignored):

```bash
python scripts/docs/populate_archive.py
```

See [MANIFEST.md](MANIFEST.md) for the path list.

## Local `docs/archive/` directory

Everything under `docs/archive/` except this README and `MANIFEST.md` is **gitignored**.
Use it only for optional local copies; do not rely on it in CI or releases.
