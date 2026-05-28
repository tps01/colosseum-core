Output artifacts
================

| File | Description |
|------|-------------|
| ``debug.log`` | Run header and execution log |
| ``execution.sqlite`` | Measurements, verifications, events, metadata |
| ``summary.txt`` | End-of-run human summary (written by ``col.endex()``) |

The output directory is created on first log or database write. Suite runs use the suite ``name`` as the directory stem.

Use :func:`col.database.read_verifications` for inspection only; do not use read helpers to decide pass/fail (use ``col.endex()``).
