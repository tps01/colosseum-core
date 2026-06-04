# Historical documentation archive

Normative documentation for Colosseum is:

- [docs/scope.md](../scope.md) — implemented behavior and deferred items
- [docs/sphinx/source/guides/](../sphinx/source/guides/) — user guides (built by docgen)
- [examples/configs/](../../examples/configs/) — bench TOML patterns
- Runtime code and generated bench config reference (`python scripts/docgen/build_all.py`)

## Tracked planning archive

Early ADRs, FFOs, and DDDs live under [planning/](planning/). They remain in git for design history but should not drive day-to-day implementation without checking scope, guides, and code first.

## Recovering older removed files

Some pre-archive design files were **removed from the git tree** earlier to reduce drift.
They are not in a normal clone. Recover them from the snapshot tag:

```bash
git fetch --tags
git tag -l doc-snapshot-pre-archive
git show doc-snapshot-pre-archive:scratchpad/colosseum_architecture_document.md
```

To copy manifest-listed paths into a local gitignored copy under `docs/archive/` (optional):

```bash
python scripts/docs/populate_archive.py
```

See [MANIFEST.md](MANIFEST.md) for paths recoverable only from the tag.

## Local gitignored copies

`python scripts/docs/populate_archive.py` writes tag-recovered files under `docs/archive/` paths listed in MANIFEST. Those copies are gitignored except `README.md`, `MANIFEST.md`, and everything under `planning/`.
