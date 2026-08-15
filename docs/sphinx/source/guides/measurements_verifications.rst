Measurements, commands, and verifications
==========================================

Core records decorated API calls in ``execution.sqlite`` and ``debug.log``.

Commands
--------

``@command`` records setup and action calls. A required command failure contributes to
the final run status. ``optional=True`` records a failure without failing the run.

Measurements
------------

``@measurement`` records a returned value under a required ``key``. Keys are unique for
the same domain, command, and row index. Use ``multi_row=True`` for indexed series.

Verifications
-------------

``@verification`` records ``PASS``, ``FAIL``, or ``ERROR``. A verifier may declare
``MeasurementSource`` values so missing evidence becomes an explicit ``ERROR`` before
the verifier body runs.

Optional verifications may fail without failing the aggregate result.

Domains
-------

The defining package may set ``__colosseum_domain__`` to choose the SQLite evidence
domain. A function-level ``__colosseum_domain__`` override takes precedence. APIs without
an override use ``core``.
