Exit codes
==========

Colosseum uses a single-bit policy in v1:

.. list-table::
   :header-rows: 1

   * - Code
     - Meaning
   * - ``0``
     - All required verifications passed; no suite/setup/teardown failure
   * - ``1``
     - Otherwise

Optional verifications (``optional=True``) are recorded and appear in ``summary.txt`` but do not change the exit code.

Call ``col.endex()`` at the end of direct-Python tests to flush artifacts and exit with the correct code.
