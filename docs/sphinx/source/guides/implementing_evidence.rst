Implementing evidence APIs
==========================

This page is for plugin authors. Test authors should start with
:doc:`measurements_verifications`; :doc:`plugins` shows registration and API
module examples.

Decorators at the plugin boundary
---------------------------------

Use ``@command`` for actions, ``@measurement`` for returned evidence, and
``@verification`` for acceptance checks. The wrappers record evidence and
apply execution modes; script authors call the resulting APIs directly.

Commands strip ``key=`` and ``optional=`` before invoking a body that does not
declare those arguments. Per-key parameter fields override command arguments.
Measurements also strip an undeclared ``optional=``; a measurement needs a key
unless automatic keying is enabled. Identity consists of domain, command, key,
and row index. Use ``multi_row=True`` for indexed series. See
:doc:`using_parameters` for parameter loading and export behavior.

A ``bytes`` measurement is returned to the caller unchanged and serialized as
``{"encoding": "hex", "data": "<hex>", "nbytes": N}`` in SQLite. Other values
must be suitable for the evidence serialization contract.

Following a decorated call through core
---------------------------------------

For a voltage-style check, first follow ``@measurement`` in
``decorators/measurement.py``, then ``@verification`` in
``decorators/verification.py``. Each wrapper has three recognizable stages:

1. **Before the body:** obtain the runtime, check the execution mode, resolve
   the key, and handle parameter export or dry-run logging. Automatic keys are
   assigned by ``resolve_auto_key`` in ``_common.py``. A skipped/exported/logged
   call returns without running the body. A configured dry-run substitute can
   return a value in place of the body.
2. **Arguments at the body:** matching parameter fields override caller
   keywords. Wrapper-owned fields such as ``optional`` and ``requirements``
   are retained for recording and removed from the body call when undeclared.
   An explicitly supplied measurement ``key`` is forwarded; only an automatic
   measurement key can be stripped when the body does not declare it.
   ``coerce_units`` resolves explicit unit values just before invocation.
   Measurement wrappers only take ``optional`` from their parameter section;
   explicit ``load_parameter`` collection coercion is a separate operation.
3. **After the body:** a measurement records its value and returns the original
   object. A verifier normalizes a measured value against supplied limits, a
   boolean into PASS/FAIL, or an explicit ``VerificationResult`` directly.
   It records and returns that result. Required FAIL/ERROR/BLOCKED outcomes
   affect the final verdict; optional outcomes remain visible without failing it.

A required command or measurement exception records ERROR and re-raises, so
the script stops unless it catches the exception. With ``optional=True`` that
exception records ERROR and returns ``None``, allowing the script to continue.
Verification-body exceptions become ERROR results and return normally; a FAIL
also returns normally. Argument/parameter validation has its own early error
paths in the wrappers, before invocation. For example, an invalid verification
parameter records ERROR without invoking the body.

Direct insertion through the database manager or SQL remains evidence-only:
an ERROR measurement row by itself does not add a scored decorator outcome.
Working call policy and the aggregator stay in Python; finalization persists
their completed conclusion for reports and later inspection.

Implementing a verifier
-----------------------

Retrieve the source measurement with
``get_context().db.get_measurement(domain, command, key, row_index=0)``.
The domain and command must match the stored identity. A mismatch returns
``None``; an ERROR measurement can instead have a row with a null value.
Check both conditions before comparing. Instrument IDs and channels are not
lookup identity fields.

Return the measured value for the decorator to compare against limit kwargs:
``expected_val`` or ``expected_result`` with optional ``tolerance``, or the
supported ``minimum`` / ``maximum`` / ``exact`` / ``expected`` arguments.
Omitting tolerance requests an exact match. Tolerance can be a numeric +/-
band, a signed one-sided band string such as ``"+10"``, or an operator such as
``">="``, ``"GE"``, or ``"!="``. A body that decides the result itself can
return ``VerificationResult`` or ``bool``.

Use ``missing_measurement_result`` when the evidence is absent. After a
required command with ``cause=unit`` failed, that helper returns BLOCKED
instead of ERROR. Finalization also inserts BLOCKED checks for configured
limit keys without measurements. Required BLOCKED outcomes fail the aggregate
result. Verification exceptions become recorded ERROR results without
aborting the procedure.

``description=`` is accepted even if the verifier body does not declare it.
It supplies the summary/report step name; blank descriptions fall back to key.
The wrapper also owns optional-outcome aggregation. See the test-author guide
for the command/measurement/verification continuation table.

Fault classification and logging
--------------------------------

A command exception of type :term:`ProceduralFault` records
``cause=procedural``. Other command exceptions record ``cause=unit``. Both
produce ERROR evidence; required command exceptions re-raise. This distinction
affects fault reporting and missing-evidence classification.

``debug.log`` records decorated calls and their resolved arguments, including
parameter overrides. Fields named ``password``, ``passwd``, ``token``,
``secret``, and ``api_key`` are redacted. Plugin internals should use
``colosseum.logging.get_logger("colosseum.<namespace>")`` so their DEBUG
messages reach the same log. Those messages are separate from recorded
operation outcomes.

Listener-thread writes
----------------------

Database inserts from listener threads use the database write queue and become
durable when finalization drains it (core 0.17.1 or newer). Stop/join workers
and drain writes before verifying their stored rows. Do not treat a successful
worker-start command as evidence that background collection finished correctly.

Domain resolution
-----------------

Evidence domain resolution happens when the decorator wraps the function:

1. Function-level ``__colosseum_domain__`` override.
2. The defining module, then parent packages' ``__colosseum_domain__``.
3. ``core`` when no override exists.

Set the package domain before importing decorated APIs, or set the API module
domain before defining them. ``register_namespace(name, module)`` supplies the
namespace name on the top-level package when no domain is already present.
It does not retroactively change domains captured by existing wrappers.
See :doc:`plugins` for a complete plugin example.
