Measurements, commands, and verifications
==========================================

Core records decorated API calls in ``execution.sqlite`` and ``debug.log``.
Plugin internals should use ``colosseum.logging.get_logger`` with
``colosseum.<namespace>`` (see :doc:`plugins`); those DEBUG lines land in the
same ``debug.log`` and are distinct from decorator pass/fail records.

What script authors see
-----------------------

You call plugin APIs; decorators record evidence automatically. The
``colosseum_template`` example from :doc:`writing_test_scripts`::

   col.template.arm_device(device_id=1)
   col.template.measure_widget_count(device_id=1, key="widgets")
   col.template.verify_widget_count(key="widgets", expected_val=10.0, tolerance=0.0)

Each call writes rows to ``execution.sqlite`` and pass/fail lines to ``debug.log``.
You do not implement decorators in test scripts. Plugin authors add them in the API
module (see :doc:`plugins`). Measurement identity is domain, command, ``key``, and
``row_index``. A ``bytes`` return value is given back to the caller unchanged and
stored as ``{"encoding": "hex", "data": "<hex>", "nbytes": N}`` so the row stays
JSON. Listener-thread inserts go through the database write queue and become
durable when the run drains that queue at finalize (requires core 0.17.1 or newer).

Commands
--------

``@command`` records setup and action calls. When a required command raises, Colosseum
records an ERROR row and event, then re-raises so remaining script steps do not run.
The runner still calls ``col.endex()`` to write the FAIL result. ``optional=True``
records the ERROR without failing the run or aborting the script.

``key=`` is stripped when the wrapped function does not declare it (the same way
``optional=`` is stripped). When a parameters file is loaded, omitted kwargs for
that key are filled from the file; call values win.

A :term:`ProceduralFault` (for example an equipment session that never opens, or
an unreadable parameters file) records ``cause=procedural`` on the command row.
Other exceptions record ``cause=unit``. Both still produce ``ERROR``. The
``debug.log`` ERROR line includes the cause and a redacted kwargs repr
(``password``, ``passwd``, ``token``, ``secret``, ``api_key``).

Measurements
------------

``@measurement`` records a returned value under a required ``key``. Keys are unique for
the same domain, command, and row index. Use ``multi_row=True`` for indexed series.

A raised exception is stored as ``status=ERROR`` with a null value, then re-raised.
``optional=True`` records that ERROR row and returns ``None`` so later steps still run.
The measurement error does not itself change the exit code. A later required
verification that needs the missing value fails, and the script can still record
other measurements. ``verify_measurement_exists`` treats the ERROR row as present.
Missing ``key=`` and duplicate keys still raise. ``optional=`` is stripped when the
wrapped function does not declare it.

Verifications
-------------

``@verification`` records ``PASS``, ``FAIL``, ``ERROR``, or ``BLOCKED``. Look up
prior measurements in the verifier body (for example
``get_context().db.get_measurement(...)``) and return
``missing_measurement_result`` when evidence is absent. After a required command
failed with ``cause=unit``, that helper returns ``BLOCKED`` instead of ``ERROR``.
At finalize, owed limit keys from the parameters file with no measurement also
become ``BLOCKED`` rows. ``overall_pass`` treats ``BLOCKED`` like ``FAIL``.

The domain string passed to ``get_measurement(domain, command, key, ...)`` must match
the domain under which the measurement was recorded (the API module's
``__colosseum_domain__``, or the namespace when set automatically). A mismatch returns
``None`` and produces a verification ERROR with ``no measurement for key=…``.

Unlike commands, verification exceptions become ``VerificationResult(status="ERROR")``
and do not abort the script. Optional verifications may fail without failing the
aggregate result.

Domains
-------

Evidence is stored under a domain string. Resolution order:

1. Function-level ``__colosseum_domain__`` override.
2. Defining module, then parent packages' ``__colosseum_domain__``.
3. Fallback ``core`` when no override is present.

This resolution happens when the decorator wraps the function. Set the package
domain before importing decorated APIs, or set it on the API module before
defining them. ``register_namespace(name, module)`` supplies the namespace name
on the top-level package when no domain is already present, but it does not
retroactively change domains captured by existing wrappers. See :doc:`plugins`.
