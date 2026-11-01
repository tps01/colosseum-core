Evidence and verification
=========================

Plugin calls record what the procedure did and what it found. Test scripts use
these APIs directly; plugin authors implement their decorators (see
:doc:`implementing_evidence`).

.. list-table::
   :header-rows: 1

   * - Operation
     - Purpose
     - Example
   * - Command
     - Change state or perform an action; record its outcome.
     - Enable a power supply output.
   * - Measurement
     - Record a returned value under an evidence key.
     - Read the rail voltage.
   * - Verification
     - Compare evidence or application state with acceptance criteria.
     - Check that the recorded voltage is within limits.

Recording and checking a value
------------------------------

A measurement key identifies a recorded result. A verification uses that key to
retrieve the measurement and compare it with its expected value. With Shared
installed, put this evidence recording demonstration inside ``main()``::

   col.shared.measure_value(key="dut_rail_v", value=3.3)
   col.shared.verify.verify_field(key="dut_rail_v", expected_val=3.3, tolerance=0.1)

This records a literal; it does not measure hardware. Verification can occur
later in the procedure. The value must have been recorded before it is checked.
See :doc:`quickstart` for complete files and the run command.

Keys, instruments, and rows
---------------------------

A measurement's identity is its **domain, command, key, and row index**. A
domain identifies the plugin evidence family, and a command identifies the
measurement function. Most measurements have row index 0. APIs that support
``multi_row`` can record indexed series under one key.

Instrument IDs and channels are call arguments; they are not part of that
identity. Two DMMs calling ``measure_voltage`` with the same key in one slot
collide. Use ``rail_a_v`` and ``rail_b_v`` even when the DMM IDs differ.
Repeating the same identity raises an error rather than replacing the value.
Each suite slot has its own evidence database.

Plugin verifiers generally know the originating domain and command. A DMM
``verify_voltage`` can therefore use just the key. It does not verify a DMM
``fetch`` row, which has a different command identity. Shared's field and regex
verifiers instead select the latest matching key across **all** domains and
commands. Reusing a key in another plugin can change what those verifiers check.

Outcomes and continuation
-------------------------

.. list-table::
   :header-rows: 1

   * - Outcome
     - Meaning
   * - PASS
     - The verification met its criteria.
   * - FAIL
     - The verification completed but its criteria were not met.
   * - ERROR
     - An operation or verification could not complete correctly.
   * - BLOCKED
     - A verification could not be performed because earlier work prevented it.

A required verification with FAIL, ERROR, or BLOCKED fails the overall run.
Verification failures and exceptions are recorded without aborting later test
steps. A required command exception records ERROR and re-raises, so later steps
are skipped unless the script catches it. A required measurement exception
records ERROR (null value) and re-raises; that ERROR **does** fail the aggregate
verdict even if the script catches the exception. An uncaught exception still
fails the CLI slot.

If a run ends without measuring a key with configured limits, finalization
records a BLOCKED verification. The parameter system calls these outstanding
checks *owed limits*. A missing-value verifier may also produce BLOCKED after
a required command with a unit fault; otherwise missing evidence normally
produces ERROR. See :doc:`using_parameters` and :doc:`exit_codes`.

An omitted or blank verification ``key=`` is not an ERROR. The decorator assigns
the next verification auto-key (``"1"``, ``"2"``, …), logs a warning, and stores
the row under that key — never an empty key. Prefer an explicit ``key=`` when
pairing with a measurement. Calling ``col.auto_key()`` is still required only
when measurements also omit ``key=``.

The domain string passed to ``get_measurement(domain, command, key, ...)`` must
match the domain under which the measurement was recorded (the API module's
``__colosseum_domain__``, or the namespace when set automatically). A mismatch
returns ``None`` and produces a verification ERROR with
``no measurement for key=…`` when the body returns
``missing_measurement_result``.

Measurement identity for a run is ``(domain, command, key, row_index)``. The
decorator rejects duplicates in the same run (unless ``multi_row=True``). The
SQLite ``measurements`` table is append-oriented without a UNIQUE constraint;
lookups return the newest matching row when multiple rows exist (for example
after import or direct writes).

Required and optional operations
--------------------------------

.. list-table::
   :header-rows: 1

   * - Operation with an exception or failing check
     - Default behavior
     - With ``optional=True``
   * - Command
     - ERROR fails the run and re-raises.
     - ERROR is retained; execution continues and the command does not fail the run.
   * - Measurement
     - ERROR stores a null value and re-raises.
     - ERROR stores a null value, returns ``None``, and execution continues.
   * - Verification
     - FAIL/ERROR/BLOCKED fails the run; execution continues.
     - The outcome is retained but excluded from the aggregate verdict.

Optional measurement errors do not make dependent verifications optional.
For example, with the environment variable below unset::

   col.shared.measure_env(key="missing_env", name="COLOSSEUM_DOCS_UNSET", optional=True)
   col.shared.verify.verify_field(key="missing_env", expected_val="ready")

The measurement records ERROR; the required check of its null value does not
pass. Its ``summary.txt`` has ``Overall result: FAIL`` and lists the required
verification under ``Failed required outcomes``. SQLite has a null ERROR
measurement and a failed required verification with ``optional=0``. Later steps
still run. By contrast, this intentional optional failure
allows an otherwise successful run to pass::

   col.shared.measure_value(key="trial", value=1)
   col.shared.verify.verify_field(key="trial", expected_val=2, optional=True)

In ``summary.txt``, the latter run has ``Overall result: PASS``, ``Exit code: 0``,
and a FAIL entry under ``Optional outcomes``. In SQLite, the trial measurement
has ``status='PASS'`` and the verification has ``status='FAIL', optional=1``.
Measurements have no ``optional`` column: inspect their status and the log.
See :doc:`output_artifacts` for queries and actual summary fields.

Verification labels and automatic keys
--------------------------------------

``description=`` supplies the summary label, WATS step name, and JUnit testcase
name; blank or omitted descriptions fall back to ``key``.

Call ``col.auto_key()`` near the start of a CLI-managed ``main()`` for file/log
checks that do not retrieve evidence by key. For direct Python, load config
first. Omitted measurement and verification keys then use separate counters
starting at ``"1"``. Explicit keys do not consume a number. Calling
``auto_key`` again does not reset counters; the next suite slot starts with
auto-keying off. The first generated key logs a warning about later lookups.

Numbered verification keys do not load parameter overrides; explicit keys do.
Each omitted multi-row key gets a new number, so use an explicit shared key
for a series. Without auto-keying, missing measurement keys raise; a missing
verification key only logs a debug warning and runs the body. Commands do not
receive automatic keys.
