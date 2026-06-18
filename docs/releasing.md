# Cutting a release

Releases are automated via [`.github/workflows/release.yml`](../.github/workflows/release.yml).

## Steps

1. Bump `version` in `pyproject.toml` on `main` (and any release notes you want in the commit message).
2. Commit, push to `main`.
3. Tag and push (tag must match the package version, without the `v` prefix):

   ```bash
   git tag v0.11.1
   git push origin v0.11.1
   ```

4. The **Release** workflow builds assets and creates a [GitHub Release](https://github.com/tps01/colosseum/releases) with:

   | Asset | Description |
   |-------|-------------|
   | `colosseum-<ver>-py3-none-any.whl` | Online install |
   | `colosseum-<ver>.tar.gz` | Source distribution |
   | `colosseum-<ver>-offline-<os>-<arch>-pyXY.tar.gz` | End-user air-gapped bundle (×4: Linux/Windows × py39/py311) |
   | `colosseum.pdf` | End-user run guide + public API (commands, measurements, verifications) |
   | `colosseum-docs-html.zip` | Same docs as browsable HTML |

   GitHub also attaches its own **Source code** zip/tarball; that archive is not a substitute for the wheel or offline bundles.

## Re-run or dry-run

- **Re-publish a tag:** delete the GitHub Release (and optionally the tag), fix `main`, then re-tag and push.
- **Build without a release:** run the workflow manually (**Actions → Release → Run workflow**). Artifacts appear on the workflow run; no Release is created without a tag push.

## Prerequisites

- Repository **Actions** enabled.
- Default `GITHUB_TOKEN` can create releases (`contents: write` is set on the workflow).
