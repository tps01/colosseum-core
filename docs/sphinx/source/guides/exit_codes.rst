Exit codes
==========

Colosseum uses a single-bit policy in v1:

.. list-table::
   :header-rows: 1

   * - Code
     - Meaning
   * - ``0``
     - All required verifications and commands passed. For suites, all **test** slots
       passed and session ``suite_failed`` is unset (with ``fail_fast = false``,
       setup, ``between_tests``, and teardown outcomes do not fail the suite).
   * - ``1``
     - Otherwise (including a required command ERROR)

Optional verifications and optional commands (``optional=True``) are recorded and
appear in ``summary.txt`` but do not change the exit code. An optional measurement
error is recorded with a null value and does not abort the script. It is not an
aggregator outcome, so it does not change the exit code by itself. A required
verification of that missing value still fails the run.

Call ``col.endex()`` at the end of direct-Python tests to flush artifacts and exit with the correct code.
