Exit codes
==========

Colosseum uses a single-bit policy in v1:

.. list-table::
   :header-rows: 1

   * - Code
     - Meaning
   * - ``0``
     - All required verifications, commands, and measurements passed. For suites,
       all **test** slots passed and session ``suite_failed`` is unset. Supporting
       slot failures (setup, ``between_tests``, teardown) always set
       ``suite_failed``.
   * - ``1``
     - Otherwise (including a required command or measurement ERROR)

Optional verifications and optional commands (``optional=True``) are recorded and
appear in ``summary.txt`` but do not change the exit code. An optional measurement
error is recorded with a null value and does not abort the script; it does not
change the exit code by itself. A **required** measurement ERROR fails the run
even if the script catches the exception. A required verification of a missing
value still fails the run.

Call ``col.endex()`` at the end of direct-Python tests to flush artifacts and exit with the correct code.
