# CI timing and profiling

How to measure GitHub Actions job duration for this repository, interpret results, and track regressions.

## Workflows

| Workflow | File | When it runs |
|----------|------|--------------|
| CI | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | Every push/PR to `main` / `master` |
| Documentation | [`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) | Manual (`workflow_dispatch`) |
| Release | [`.github/workflows/release.yml`](../../.github/workflows/release.yml) | Version tags / manual |

The **CI** workflow runs ten parallel jobs on each PR (test matrix ×4, visa_sim ×2, docgen, static analysis, packaging, offline bundle smoke). **Wall-clock** for a PR is roughly the slowest job, not the sum of all jobs. **Billable minutes** are the sum of all job durations.

## Per-run step timing (instrumented CI)

Each CI job writes a **Job timing** section to the GitHub Actions run summary (`GITHUB_STEP_SUMMARY`). Open a workflow run → select a job → **Summary** tab.

The `docgen` and `offline-install` jobs also set `COLOSSEUM_CI_TIMING=1`, which prints lines like `TIMING staging=12.3s` in the job log for Python phases:

| Job | Log phases |
|-----|------------|
| docgen | `staging`, `html`, `latex`, `latexmk` (via `build_pdf.py`) |
| offline-install | `build_artifacts`, `download_wheels`, `stage_bundle`, `create_tarball` (via `package_offline.py`) |

The docgen job is split into separate timed steps: **Install LaTeX toolchain**, **Docgen staging**, **Docgen HTML**, **Docgen PDF**.

## Historical baseline from GitHub

Requires the [GitHub CLI](https://cli.github.com/) (`gh auth login`):

```bash
python scripts/ci/summarize_runs.py
python scripts/ci/summarize_runs.py --workflow ci.yml --limit 30 --conclusion success
python scripts/ci/summarize_runs.py --markdown build/ci-timing/summary.md --csv build/ci-timing/jobs.csv
```

Output ranks jobs by **median** and **p90** duration (seconds). Use this for a one-off audit before changing CI.

## Local mirror of CI jobs

Run the same commands as a CI job on your machine:

```bash
python scripts/ci/profile_local.py --job docgen
python scripts/ci/profile_local.py --job docgen-html
python scripts/ci/profile_local.py --job test
python scripts/ci/profile_local.py --job static
python scripts/ci/profile_local.py --job offline
python scripts/ci/profile_local.py --job packaging
```

Set `COLOSSEUM_CI_TIMING=1` is applied automatically for `docgen` and `offline`. For slow unit tests locally, use [`scripts/profile_unit_tests.py`](../../scripts/profile_unit_tests.py).

## Measured baseline

Data collection uses [`scripts/ci/summarize_runs.py`](../../scripts/ci/summarize_runs.py) (requires `gh auth login`):

```bash
python scripts/ci/summarize_runs.py --workflow ci.yml --limit 20 --conclusion success
python scripts/ci/summarize_runs.py --markdown build/ci-timing/summary.md --csv build/ci-timing/jobs.csv
python scripts/ci/summarize_runs.py --run-id RUN_ID --job-filter docgen
```

### Pre-optimization (instrumented CI, no LaTeX cache)

Recorded from workflow structure and typical `ubuntu-latest` runs **before** the LaTeX apt cache step (June 2026). Step times come from job **Summary** tabs once an instrumented run completes; job-level medians from `summarize_runs.py`.

**Top jobs by expected wall-clock** (hypothesis rank — confirm with `summarize_runs.py`):

| Rank | Job | Typical median | Notes |
|------|-----|----------------|-------|
| 1 | documentation pdf artifact | 8–15 min | Dominated by cold `apt-get install texlive-latex-extra` |
| 2 | offline bundle smoke | 3–8 min | Wheel download + venv install |
| 3 | pytest (windows-latest, py3.11) | 2–5 min | Slower runner + matplotlib |
| 4 | static analysis (py3.11) | 1–3 min | mypy over four packages |
| 5 | pytest (ubuntu-latest, py3.11) | 1–2 min | Reference for matrix delta |

**Docgen job — step breakdown to capture** (from run Summary after instrumentation):

| Step | Pre-cache expectation | Primary cost |
|------|----------------------|--------------|
| Install | 30–90 s | pip `.[docs,test]` |
| Install LaTeX toolchain | **180–480 s** | cold apt + `texlive-latex-extra` |
| Docgen staging | 30–120 s | autodoc + stitch |
| Docgen HTML | 60–180 s | `sphinx-build -b html` |
| Docgen PDF | 60–240 s | `sphinx-build -b latex` + `latexmk` |

Log lines (`COLOSSEUM_CI_TIMING=1`): `TIMING staging=…`, `TIMING html=…`, `TIMING latex=…`, `TIMING latexmk=…`.

**Decision:** LaTeX apt install is expected to exceed Docgen PDF → first optimization is **apt/texlive cache** in [`ci.yml`](../../.github/workflows/ci.yml) (added June 2026).

### Post-optimization (LaTeX apt cache)

After merging the cache step, re-run CI and compare **Install LaTeX toolchain** in the docgen job Summary:

| Step | Pre-cache (cold) | Post-cache (2nd+ run) | Target |
|------|------------------|------------------------|--------|
| Install LaTeX toolchain | 180–480 s | **10–60 s** | Cache hit on `/var/cache/apt/archives` + `/usr/share/texlive` |
| Docgen staging / HTML / PDF | unchanged | unchanged | — |
| documentation pdf artifact (job total) | 8–15 min | **4–8 min** | ~50% job time reduction |

Update this table with measured values from the first cached run (`Actions → CI → documentation pdf artifact → Summary`) and paste job medians from:

```bash
python scripts/ci/summarize_runs.py --limit 5 --conclusion success
```

## Expected bottlenecks (hypotheses — validate with data)

These are the usual suspects; confirm with `summarize_runs.py` and job summaries after the instrumentation lands:

1. **Docgen — LaTeX apt install** — `texlive-latex-extra` is installed on every run with no apt cache; often dominates the docgen job before any Sphinx work.
2. **Docgen — PDF build** — `sphinx-build -b latex` plus `latexmk` after staging/HTML; compare step summary times for **Docgen PDF** vs **Install LaTeX toolchain**.
3. **Offline bundle smoke** — builds sdist/wheel, downloads `[bench]` wheels, creates tarball, installs into a fresh venv (`run_offline_install_check.py`).
4. **Test matrix on `windows-latest`** — full tiers 1–3 with `.[test,plot]`; Windows runners are typically slower than Ubuntu.
5. **Static analysis** — mypy strict over four packages often exceeds ruff/bandit/vulture; run per-tool locally with `profile_local.py --job static`.

## Optimization backlog (after profiling)

Do not apply these until step summaries or `summarize_runs.py` confirm the bottleneck:

| If data shows… | Candidate change |
|----------------|------------------|
| LaTeX apt ≫ PDF build | Cache apt/texlive (**done** — see Measured baseline); prebuilt TeX action if cache insufficient |
| Staging/autodoc ≫ sphinx | Cache `build/docgen/` keyed on source hashes |
| PDF slow on every PR | Build PDF on release/tags only; keep HTML in CI (`--skip-pdf`, as in `docs.yml`) |
| Offline job slow | Cache wheelhouse; path-filter to packaging-related changes |
| Windows test slow | Path filters; reduce matrix duplication |
| mypy slow | Cache `.mypy_cache`; optional PR diff scope |

## Related

- [Testing README](README.md) — pytest tiers, static analysis, unit-test profiling
- [`.github/actions/step-timer`](../../.github/actions/step-timer) — composite action used in CI
- [`scripts/docgen/build_all.py`](../../scripts/docgen/build_all.py) — `--stage-only`, `--html-only`, `--pdf-only` phase flags
