# Relaxed TOML fuzzing

One core-only Atheris target checks malformed UTF-8/TOML, preprocessing
idempotence, quoted-string preservation, generated bare words, boolean aliases,
and multiline string preservation. It does not load plugins or bootstrap runs.
Only known-valid generated TOML is compared with the standard parser, since
relaxed parsing intentionally changes some other TOML values.

On Linux AMD64 with Python 3.12, install `requirements.txt`, then from core's root:

```sh
mkdir -p .fuzz-work/corpus .fuzz-work/artifacts
cp -n tests/fuzz/corpus/* .fuzz-work/corpus/
python -m tests.fuzz.toml_relaxed .fuzz-work/corpus -max_total_time=30 -max_len=4096 -timeout=5 -artifact_prefix=.fuzz-work/artifacts/
```

Use a larger `-max_total_time` for longer exploration. Replay a failure by replacing
the corpus directory argument with its artifact filename. Reduce discoveries and
keep named pytest regressions before fixing them. Generated files are ignored;
tracked seeds also run in normal pytest without Atheris. CI runs this bounded
target only on Ubuntu/Python 3.12. No equipment installation is required.
Atheris is Apache-2.0: https://github.com/google/atheris/blob/master/LICENSE


## Incremental coverage

The target now checks three additional areas on each accepted UTF-8 input:

1. Basic/literal multiline strings, three-to-five closing quotes, line
   continuations, CRLF, and relaxation resuming after a closed string.
2. Multiline arrays, inline tables, quoted keys, integer bases and signs,
   scientific notation, and special float literals (`inf`/`nan`). Generated
   standard TOML is checked against `tomllib`, including numeric types.
3. Parsed sections through `normalize_sections` and `ConfigStore`: preserved
   rows, table/array equivalence, row-order independence, sorted lookups,
   duplicate/invalid IDs, missing required fields, and input preservation on
   success and rejection. The spec is local and never registered as a plugin.

All three reuse the same corpus, CLI, and bounded CI job. Named regressions
cover signed infinity/NaN values being silently converted into strings.


## Database evidence and write queue

The separate `tests.fuzz.database` target uses a fresh temporary on-disk database
per input and up to 17 bounded actions: enqueue, drain, synchronous insert after
a barrier, flush, close, repeated close, read-only reopen, and rejected writes
after close. It tests both commit modes, JSON-compatible values, Unicode/NUL
text, repeated keys and row indices, scoped lookups, and latest-row selection.
Rows are compared with an independent model and a separate SQLite connection
at durability boundaries. Temporary databases are removed after each input.
Failure batches now verify apply/commit-error propagation and rollback of only
uncommitted rows. Event-coordinated enqueue/stop scenarios verify accepted jobs
finish and writes after the closing boundary are rejected. There are no timing
sleeps or installed-plugin discovery.

```sh
mkdir -p .fuzz-work/database/corpus .fuzz-work/database/artifacts
cp -n tests/fuzz/database_corpus/* .fuzz-work/database/corpus/
python -m tests.fuzz.database .fuzz-work/database/corpus -max_total_time=30 -max_len=512 -timeout=5 -artifact_prefix=.fuzz-work/database/artifacts/
```

CI runs this independently of TOML fuzzing. The seeds are also normal pytest
cases using the production manager and background queue on Windows and Linux.


## Results and finalization

`tests.fuzz.results` compares up to 32 generated outcomes with independent
required/optional counts and scoring. It checks ordering independence of scores,
summary counts/status/JSON serialization, summary purity, suite/teardown errors,
and failure remaining after adding a passing result.

`tests.fuzz.finalization` uses isolated in-memory databases and local registries.
Generated flags select single-run or suite-slot policies, required failures,
shutdown-hook and resource-close failures, an asynchronous storage failure,
owed limits, and teardown failure. It checks settled evidence, owed BLOCKED
rows, cleanup, shutdown isolation for suite slots, and repeated `endex()` calls
without replaying shutdown or cleanup. Global context and diagnostic patches
are restored after each input. There is no installed-plugin discovery or disk
report rendering in these targets.

Both have separate CI jobs/corpora. To run manually, replace `TARGET` below
with `results` (max length 512) or `finalization` (max length 128):

```sh
mkdir -p .fuzz-work/TARGET/corpus .fuzz-work/TARGET/artifacts
cp -n tests/fuzz/TARGET_corpus/* .fuzz-work/TARGET/corpus/
python -m tests.fuzz.TARGET .fuzz-work/TARGET/corpus -max_total_time=30 -max_len=128 -timeout=5 -artifact_prefix=.fuzz-work/TARGET/artifacts/
```

`finalize_run` is intentionally called once per slot. Repeated-finalization
checks use the single-run `endex` entry point, which owns the idempotence guard.


## Inspect coverage manually

With developer requirements installed, replay a target's tracked seeds and
generate HTML, JSON, and terminal line/branch reports on Windows or Linux:

```sh
python -m tests.fuzz.coverage_report toml_relaxed
python -m tests.fuzz.coverage_report database
python -m tests.fuzz.coverage_report results
python -m tests.fuzz.coverage_report finalization
```

To inspect an evolved corpus instead, supply its directory:

```sh
python -m tests.fuzz.coverage_report toml_relaxed --corpus .fuzz-work/corpus
```

Reports go to `.fuzz-work/coverage/TARGET/` (or `--output`).
Each input is replayed once; this does not mutate the corpus or perform random
exploration. It calls the same `check_input()` used by Atheris/pytest directly,
so the fuzzing engine is not required and coverage is saved normally. Background
threads are traced for the database/queue targets. Reports are scoped to
relevant production modules, excluding harness code and third-party libraries.
Some functions in those modules are deliberately outside a target's scope;
read the missing lines/branches before treating a percentage as a test gap.

Coverage is slower than normal fuzzing. Keep this manual diagnostic separate
from the existing short CI runs; no coverage threshold is enforced.


The first coverage review found that the mixed result seeds reached suite errors
before required failures, hiding the direct required-failure scoring branch.
Dedicated required-only and optional-only failure seeds now exercise that path
independently. The reports also show intentionally untested areas such as full
config startup, suite-container finalization, and disk report rendering; those
need their own scenarios rather than a larger generic byte dictionary.


Use an isolated project environment for the current developer requirements.
Older mutation-testing environments using `mutatest==3.1.0` require coverage.py
below 6 and cannot share the coverage.py 7 dependency used by this reporter.
The Linux container validation leaves the host's Python packages untouched.


## Deeper lifecycle scenarios

Database checks now include deterministic apply/commit failures: an already
committed row survives, the failing batch rolls back, errors reach drain/stop,
and later writes are rejected. Explicit events coordinate enqueue/stop tests;
they do not depend on random sleeps.

`disk_finalization` cross-checks real SQLite evidence, stored outcome facts,
summary JSON/text, and finalized directory names. It also exercises report-write
and directory-rename failures. A single-run report-write failure propagates and
makes `endex` exit with failure on subsequent calls; its already stored scoring
snapshot remains available. Rename failures retain the original directory.

`suite_finalization` finalizes real setup/test/teardown slot artifacts and a suite
container, varying repeats, scored/excluded slots, supporting-phase failures,
and fail-fast facts. It checks totals, persisted occurrences and rebased paths,
shutdown once for the container, and completed-suite `endex`. Suite report-write
failures retain the suite's scoring exit code, matching the existing contract.
This generates finalized slot facts, not full scheduler execution sequences.

Both new targets use separate `TARGET_corpus` directories and the same manual
commands as the results targets, with `-max_len=64`. The coverage reporter also
accepts their names. CI keeps a 30-second smoke budget; use `-max_total_time=60`
or longer manually to continue exploring a preserved corpus.


Disk and suite finalization use a 15-second per-input timeout in CI because a
single input performs multiple real SQLite/file operations. Other targets keep
the 5-second limit. A timeout artifact found under concurrent local load was
replayed successfully alone and retained as the `support-only` suite seed;
it was not a reproducible production defect.
