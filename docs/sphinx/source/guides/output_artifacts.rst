Output artifacts
================

Each completed test run writes evidence under ``outputs/``. See :doc:`running_tests`
for directory naming and :doc:`writing_test_scripts` for a full example run.

.. list-table::
   :header-rows: 1

   * - File
     - Description
   * - ``debug.log``
     - Run header and execution log. Lines use ``%(name)s`` (for example
       ``[colosseum.template]``). Plugin code must call
       ``colosseum.logging.get_logger`` with ``colosseum.<namespace>`` so
       DEBUG records reach this file (see :doc:`plugins`).
   * - ``execution.sqlite``
     - Measurements, verifications, events, and metadata
   * - ``summary.txt``
     - End-of-run human summary (written by ``col.endex()``)
   * - ``summary.json``
     - End-of-run machine-readable summary (same data as ``summary.txt``)
   * - ``wats_<datetime>_<script>.json``
     - Optional WATS WSJF JSON report. Written only when the ``wats`` report
       listener is enabled (see below).
   * - ``junit.xml``
     - Optional JUnit XML report. Written only when the ``junit`` report
       listener is enabled.

Every run with artifacts still writes ``debug.log``, ``execution.sqlite``,
``summary.txt``, and ``summary.json``. Opt-in report listeners never replace
those defaults.

JSON and JUnit reports (opt-in)
-------------------------------

Enable report listeners in config or on the CLI::

   [colosseum.reports]
   wats = false
   junit = false

Both default to false when the table is absent. ``colosseum run`` and
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

The output directory is created on first log or database write. By default, timestamped
run folders are created under ``outputs/`` relative to the process working directory.
Use ``-o/--output-dir`` on the CLI to choose a different output root (see
:doc:`running_tests`). Suite runs use the suite ``name`` as the directory stem. Completed
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
decide pass/fail (use ``col.endex()``). The operator GUI browses completed
runs through ``summary.json`` and ``debug.log``. It does not provide a
SQLite measurement, verification, or event-table browser.
