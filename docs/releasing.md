# Cutting a release

1. Validate `develop` with tests, static analysis, docs, and `python -m build`.
2. Update the version in `pyproject.toml` and `colosseum/__init__.py`.
3. Merge `develop` into release-only `main`.
4. Tag `main` with `v<version>` and push the tag.

The tag must match `project.version`. The release workflow publishes:

- `colosseum_core-<version>-py3-none-any.whl`
- `colosseum_core-<version>.tar.gz`
- core PDF and HTML documentation

Cross-distribution or offline bundles are owned by a separate integration/release project,
not by core.
