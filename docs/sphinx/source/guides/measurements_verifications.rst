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
``optional=`` is stripped). When a parameters file is loaded, kwargs for that
key are filled from the file. A field in the file overrides the call.

A :term:`ProceduralFault` (for example an equipment session that never opens, or
an unreadable parameters file) records ``cause=procedural`` on the command row.
Other exceptions record ``cause=unit``. Both still produce ``ERROR``. The
command ERROR line in ``debug.log`` includes that cause.

``debug.log`` records every command, measurement, and verification call with the
arguments that were used, including values filled from a parameters file. A
field in the file overrides the call. ``password``, ``passwd``, ``token``,
``secret``, and ``api_key`` are redacted.

Measurements
------------

``@measurement`` records a returned value under a required ``key``. Keys are unique for
the same domain, command, and row index. Use ``multi_row=True`` for indexed series.

A raised exception is stored as ``status=ERROR`` with a null value, then re-raised.
``optional=True`` records that ERROR row and returns ``None`` so later steps still run.
The measurement error does not itself change the exit code. A later required
verification that needs the missing value fails, and the script can still record
other measurements. ``verify_measurement_exists`` treats the ERROR row as present.
Duplicate keys still raise. A missing ``key=`` raises unless the procedure called
:term:`auto_key`. ``optional=`` is stripped when the wrapped function does not
declare it.

Verifications
-------------

``@verification`` records ``PASS``, ``FAIL``, ``ERROR``, or ``BLOCKED``. Look up
prior measurements in the verifier body (for example
``get_context().db.get_measurement(...)``) and return the measured value; the
decorator compares it to limit kwargs (``expected_val`` with optional
``tolerance``, or ``minimum`` / ``maximum`` / ``exact`` / ``expected``). Omit
``tolerance`` for an exact match. ``tolerance`` may be a ± number, a signed
one-sided band string such as ``"+10"``, or an operator (``">="``, ``"GE"``,
``"!="``, and so on). Return ``missing_measurement_result`` when evidence is
absent, or return ``VerificationResult`` / ``bool`` when the body decides the
outcome itself. After a required command failed with ``cause=unit``, that helper
returns ``BLOCKED`` instead of ``ERROR``. At finalize, owed limit keys from the
parameters file with no measurement also become ``BLOCKED`` rows.
``overall_pass`` treats ``BLOCKED`` like ``FAIL``.

The domain string passed to ``get_measurement(domain, command, key, ...)`` must match
the domain under which the measurement was recorded (the API module's
``__colosseum_domain__``, or the namespace when set automatically). A mismatch returns
``None`` and produces a verification ERROR with ``no measurement for key=…``.

Unlike commands, verification exceptions become ``VerificationResult(status="ERROR")``
and do not abort the script. Optional verifications may fail without failing the
aggregate result.

``description=`` is optional on every verification, even when the wrapped function
does not declare it. When set, it is the WATS step name, the label beside
``[verification]`` in ``summary.txt``, and the JUnit testcase name. When it is
omitted or blank, those names fall back to ``key``.

Automatic keys
--------------

Call ``col.auto_key()`` near the top of ``main()`` when a procedure checks
downloaded files or logs and does not need a meaningful evidence key. Under
``colosseum run`` the runtime already exists, so it can be the first call. A
direct ``python`` script calls it after ``col.config.load_config()``.

After that call, a measurement or verification that omits ``key=`` (or passes
a blank key) is stored under the next integer for that family. The first
measurement without a key is ``"1"``, then ``"2"``, and so on. Verifications
have their own counter, also starting at ``"1"``. An explicit ``key=`` is
stored as given and does not consume a number. A second ``col.auto_key()`` in
the same procedure does not restart the counters. The next suite slot starts
with auto-keying off.

The first time a key is filled in, Colosseum logs one warning:
``Autokeying has taken place. Later verifications may fail due to not having
the correct keys.`` Later numbered calls stay on the normal evidence line
(``key=2``, and so on) without repeating the warning.

Numbered verification keys are not looked up in a parameters file. Explicit
keys still are. ``multi_row`` calls that omit ``key=`` each receive the next
integer; pass ``key=`` when a series must share one key. Commands are
unchanged. Without ``col.auto_key()``, a missing measurement key still raises
and a missing verification key is still recorded as an ERROR.

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
