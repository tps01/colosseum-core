Output artifacts
================

Each completed test run writes evidence under ``outputs/``. See :doc:`running_tests`
for directory naming and :doc:`writing_test_scripts` for a full example run.

.. list-table:: What to inspect first
   :header-rows: 1

   * - Need
     - File
   * - Quick overall outcome
     - ``summary.txt``
   * - Automated post-processing
     - ``summary.json``
   * - Troubleshooting an operation
     - ``debug.log``
   * - Querying recorded measurements and verification rows
     - ``execution.sqlite``
   * - CI results
     - ``junit.xml`` (when enabled)
   * - WATS integration
     - ``wats_<datetime>_<script>.json`` (when enabled)

.. list-table::
   :header-rows: 1

   * - File
     - Description
   * - ``debug.log``
     - Run header, execution log, and a provenance block (platform,
       core and plugin package versions, and MD5 hashes of the input files). Lines use ``%(name)s``
       (for example ``[colosseum.template]``). Plugin code must call
       ``colosseum.logging.get_logger`` with ``colosseum.<namespace>`` so
       DEBUG records reach this file (see :doc:`plugins`). The provenance
       block is appended to this file only; it is not printed on the console.
   * - ``execution.sqlite``
     - Measurements, verifications, events, metadata, and a ``provenance``
       table (``platform``, ``packages``, and ``inputs`` sections)
   * - ``summary.txt``
     - End-of-run human summary (written by ``col.endex()``). Provenance is
       not copied here.
   * - ``summary.json``
     - End-of-run machine-readable summary, including a ``provenance`` object
       with the same platform, package, and input data as ``debug.log``
   * - ``wats_<datetime>_<script>.json``
     - Optional WATS WSJF JSON report. Written only when the ``wats`` report
       listener is enabled (see below).
   * - ``junit.xml``
     - Optional JUnit XML report. Written only when the ``junit`` report
       listener is enabled.

Every run with artifacts still writes ``debug.log``, ``execution.sqlite``,
``summary.txt``, and ``summary.json``. Opt-in report listeners never replace
those defaults.

Script and suite summaries include UTC start and end timestamps and a runtime
measured using a monotonic clock. ``summary.json`` exposes the elapsed time as
``duration_seconds``; it can differ from the timestamp difference if the system
clock changes. Existing summaries are not updated retroactively.

Completed results in SQLite
---------------------------

Raw ``measurements`` retain their existing columns, append behavior, JSON
encoding, and lookup/list ordering, including undecorated plugin series.
Three core-owned tables add inspectable completion data:

* ``verification_requirements`` attaches each requirement ID to its source
  verification ID and zero-based ordinal. Repeated IDs and first-seen ordering
  are retained. Owed-limit BLOCKED verifications retain their configured IDs.
* ``run_result`` has at most one row (``id=1``), with ``kind``,
  ``overall_result``, ``exit_code``, ``completed_at``, ``format_version=1``,
  and ``payload_json``. The payload contains the existing summary JSON fields,
  plus ``outcomes`` and ``optional_outcomes`` with scored kind, identity,
  status, optionality, message, cause, description, and requirement IDs.
  ``stored_status`` mirrors legacy status metadata (PASS/FAIL, or N/A for
  supporting slots). Raw sample payloads
  are not duplicated. The snapshot and legacy result metadata commit together.
* The suite container's ``suite_slot_results`` has one row per occurrence,
  identified by ``slot_id`` in execution order. Columns retain phase, script,
  relative output directory, test/repeat/cycle indexes, scoring participation,
  verdict, exit code, and the slot's compact result in ``payload_json``.
  Raw measurements remain in each slot database.

The suite's ``run_result`` payload has the existing suite summary fields:
test counts, slot lists, common failed-verification ranking, requirement
rollup, and provenance. Rollups use finalized test-slot facts, including
no-artifacts runs, rather than reading child summary files. Supporting phases
do not contribute to test statistics or requirement rollups. Requirement
failures, including optional checks, retain their existing independent
traceability semantics; they do not introduce another exit-code policy.

A missing snapshot means completion data is unavailable, not PASS. Older
supported databases remain readable without these tables. An exception after
a slot's ``endex()`` replaces that occurrence's core result and artifacts;
report callbacks are not replayed. In no-artifacts mode these facts stay in
memory and no files are created.

Query recorded evidence
-----------------------

In a SQLite client, open the **test slot's** ``execution.sqlite`` (a suite
container database holds provenance, not all slot measurements). For the
quickstart value::

   SELECT domain, command, key, row_index, value_json, units, status
   FROM measurements
   WHERE key = 'voltage'
   ORDER BY id;

The value is JSON text. For required versus optional verification outcomes::

   SELECT key, status, optional, actual_json, expected_json, message
   FROM verifications
   ORDER BY id;

``optional=1`` means that verification does not fail the aggregate result.
Measurement errors store ``status='ERROR'`` and a null value; measurements
do not have an ``optional`` column. Commands have ``optional`` and ``cause``
columns. See :doc:`measurements_verifications` for continuation behavior.

Without a separate SQLite CLI, use Python from a standalone script, replacing
the path with a completed run's database::

   import sqlite3

   with sqlite3.connect("outputs/<run>/execution.sqlite") as db:
       for row in db.execute("SELECT key, value_json, status FROM measurements ORDER BY id"):
           print(row)

Provenance
----------

Before the script runs, Colosseum records the host and the files that define
the run. A suite does this once, on the container, and does not repeat it for
each slot.

``summary.json`` stores the snapshot under ``provenance``:

- ``platform`` — ``system``, ``release``, ``version``, ``machine``,
  ``python_version``, ``python_implementation``, and ``executable`` (the
  Python binary that ran the test).
- ``packages.versions`` — the version of ``colosseum-core`` plus each plugin
  distribution that exposes a ``colosseum.plugins`` entry point, as
  ``importlib.metadata`` resolves it. Other installed packages are not listed.
  ``packages.plugins`` names those plugin distributions.
- ``inputs`` — ``role``, ``path``, and ``md5`` for each existing input file
  (script, config, metadata, parameters, and, for a suite, the suite file and
  its setup, test, between, and teardown scripts).

Provenance is intentionally lean: it does not record every installed copy of a
package or any git repository state.

``debug.log`` appends one ``Provenance:`` line per section. The ``provenance``
table stores the same three sections as JSON. ``--no-artifacts`` skips the log
file and the writable-directory check; a single run still stores the snapshot
in the in-memory database.

JSON and JUnit reports (opt-in)
-------------------------------

Enable report listeners in config or on the CLI::

   [colosseum.reports]
   wats = false
   junit = false

Both default to false when the table is absent. Use standard TOML booleans
``true`` and ``false``. ``colosseum run`` and
``colosseum run-suite`` accept ``--report wats`` and ``--report junit``
(repeatable). When any ``--report`` is present, that set replaces the config
table for the process.

When metadata is configured (config TOML ``[colosseum.metadata]`` or YAML
``test_metadata``), identity fields such as ``location``, ``process_code``, and
``uut`` populate the WATS report. Optional ``wats_folder`` copies the WATS file
to an absolute path after finalize, and is consulted only when WATS is enabled.

The WATS filename embeds a UTC timestamp and the script stem, for example
``wats_20260827T233344_my_test.json``. JUnit is always ``junit.xml`` in the
slot directory.

Example excerpts
----------------

**debug.log** (command ERROR with cause and redacted kwargs)::

   2026-10-17 18:30:01 ERROR [colosseum] command core.login key=auth status=ERROR cause=unit args={'password': '***', 'key': 'auth'}
   Traceback (most recent call last):
     ...
   RuntimeError: auth failed

**summary.txt** (abbrev.)::

   Overall: FAIL (exit 1)
   Required: FAIL=0 ERROR=1 BLOCKED=1 PASS=0
   parameters_file: C:\bench\limits.toml

**WATS** (abbrev.; ``result`` is ``F`` when a unit abort left owed limits
``BLOCKED``; ``E`` when a required ``cause=procedural`` command failed)::

   {
     "type": "T",
     "result": "F",
     "root": {
       "steps": [
         {
           "name": "rail",
           "status": "F",
           "tsGuid": "rail",
           "stepType": "ET_PFT",
           "reportText": "not measured: core.power_on: DUT silent"
         }
       ]
     }
   }

A ``BLOCKED`` step includes ``reportText`` and does not include ``numericMeas``.

**junit.xml** (abbrev.)::

   <testsuite name="my_test" tests="1" failures="1" errors="0" skipped="0">
     <testcase classname="core.owed_limit" name="rail">
       <properties>
         <property name="cause" value="unit"/>
         <property name="parameters_file" value="C:\bench\limits.toml"/>
       </properties>
       <failure message="not measured: core.power_on: DUT silent" type="BLOCKED"/>
     </testcase>
   </testsuite>

A required command ``ERROR`` with no verification rows still produces one
``testcase`` with ``<error>`` so a power-on abort is visible in CI.

Error outcomes (summary)
------------------------

.. list-table::
   :header-rows: 1

   * - Situation
     - Exit
     - Notes
   * - Required command ``ERROR`` with ``cause=unit``; owed limit never measured
     - 1
     - Verification rows ``BLOCKED``; WATS ``F`` when enabled
   * - Required ``ProceduralFault`` (``cause=procedural``)
     - 1
     - WATS ``E`` when enabled
   * - Artifacts on, no ``--report`` / reports table false
     - unchanged
     - ``summary.*`` + ``debug.log`` only; no ``wats_*.json`` / ``junit.xml``

The output directory is created on first log or database write, after a check
that the outputs root is writable. If that check fails, the run exits 1 and
does not start the script or create a timestamped folder. By default, timestamped
run folders are created under ``outputs/`` relative to the process working directory.
Use ``-o/--output-dir`` on the CLI to choose a different output root (see
:doc:`running_tests`). Suite runs use the suite ``name`` as the directory stem and
record provenance once on the container (``debug.log``, ``execution.sqlite``, and
``summary.json``). Slot folders do not repeat that snapshot. Completed
output directories are renamed with the final result, for example
``outputs/<timestamp>_<name>-pass/`` or ``outputs/<timestamp>_<name>-fail/``. Disable
persisted output with ``--no-artifacts``, ``load_config(..., no_artifacts=True)``, or
``COLOSSEUM_NO_ARTIFACTS=1`` (see :doc:`running_tests`).

Plugin-generated files (for example spectrum trace CSV, IQ capture binaries, screenshots)
are written under the same output directory. Saving a file does not automatically create a measurement artifact index:
equipment exporters explicitly record ``artifact_path`` measurements; GUI
screenshots/trees save files and sidecars without those rows; host profile
capture returns its path in the command result. Host samplers save CSV and
record compact summary measurements. All require artifacts enabled.

RF trace files from
``col.equipment.speca.save_trace_data`` typically live at ``traces/<name>.csv`` relative
to the run directory.

Equipment stores ``artifact_path`` **relative to the run directory** when the
file is inside it. After the ``-pass`` / ``-fail`` rename, open
``execution.sqlite`` in the renamed folder and resolve that relative path
against the database's directory. Older rows may still hold an absolute path
from before the rename; resolution rebases a matching suffix onto the renamed
directory when the original path no longer exists. Verification-only import
keeps the path relative to the previous run (``run_metadata.imported_from``)
so the file is found there, not in the new run folder.

Listener threads enqueue measurements. Finalize drains and closes the write
queue before renaming the directory, so those rows are committed first.
Script-thread artifact registration inserts synchronously and is visible to a
following verification in the same process. A ``bytes`` measurement value is
returned as bytes and stored as JSON ``{"encoding": "hex", "data": "...",
"nbytes": N}``. Row identity is domain, command, key, and ``row_index``.

Use ``col.database.read_verifications`` for inspection only; do not use read helpers to
decide pass/fail (use ``col.endex()``). The optional
`colosseum-extensions <https://github.com/tps01/colosseum-extensions>`__ desktop runner
(``colosseum --gui``) browses completed runs through ``summary.json`` and
``debug.log``. It does not provide a SQLite measurement, verification, or
event-table browser.
