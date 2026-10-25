Plugins and extensions
======================

Plugins are separate Python distributions discovered from setuptools entry points.
The copy-ready template lives at ``examples/plugins/colosseum_template``.
``colosseum-shared`` is a minimal first-party example (namespace only).

A working plugin needs three things at minimum. Config, evidence decorators, and
resource helpers are optional layers on top.

How a run discovers plugins, records evidence, and finalizes is
:doc:`runtime_execution`.

Overview
--------

.. list-table::
   :header-rows: 1

   * - Layer
     - What
     - Required?
   * - 0
     - Entry point, ``register_namespace``, API module
     - **Yes**
   * - 1
     - ``@command`` / ``@measurement`` / ``@verification``
     - When you need evidence
   * - 2
     - ``ConfigSectionSpec`` and config TOML rows
     - When you own config sections
   * - 3
     - Validators, shutdown hooks, connection helpers
     - When you need them

The sections below follow the template plugin (namespace ``template``, API
``col.template.*``). The same patterns apply when you rename the package and namespace.

Layer 0: Minimal plugin
-----------------------

Three touch points are required.

1. An installable package with a ``colosseum.plugins`` entry point.
2. A ``register(registry)`` function that calls ``register_namespace``.
3. An API module exposed as ``col.<namespace>.*``.

**pyproject.toml**::

   [project.entry-points."colosseum.plugins"]
   template = "colosseum_template:register"

The entry-point **key** is metadata only. The runtime namespace is the string passed
to ``register_namespace``.

**colosseum_template/__init__.py**::

   from colosseum.logging import get_logger
   from colosseum.plugins.registry import PluginRegistry

   _logger = get_logger("colosseum.template")

   def register(registry: PluginRegistry) -> None:
       from colosseum_template import api

       registry.register_namespace("template", api)
       _logger.debug("Registered col.template namespace")

After ``pip install -e .`` (or a wheel install) in the same environment as
``colosseum-core``, the namespace becomes ``col.template``. Source checkouts alone do
not provide entry-point metadata.

List ``colosseum-core`` in your plugin's ``dependencies`` (matching the version range
your release supports), or document that core must be installed first in the same
environment.

Minimal ``pyproject.toml``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Greenfield plugins need a full project file, not only the entry point::

   [build-system]
   requires = ["setuptools>=68", "wheel"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "acme"
   version = "0.1.0"
   description = "My Colosseum extension"
   requires-python = ">=3.9"
   dependencies = ["colosseum-core>=0.17.0,<0.18"]

   [project.entry-points."colosseum.plugins"]
   acme = "acme:register"

   [tool.setuptools.packages.find]
   include = ["acme*"]

Keep heavy imports inside ``register()`` so importing the package stays lightweight.

Duplicate namespaces or config sections raise ``PluginRegistrationError``. A failing
``register()`` also fails fast at load time.

First-party namespaces (choose a distinct name for your own plugin):
``equipment``, ``shared``, ``io``, ``host``, ``messaging``, and ``gui``.

Layer 1: Evidence decorators
----------------------------

Use ``command``, ``measurement``, and ``verification`` from ``colosseum.decorators``
when you need recorded pass/fail evidence. See :doc:`measurements_verifications`.
Define decorated plugin functions with keyword-only parameters (``def fn(*, ...)``)
so test scripts are immediately readable to people less familiar with Python:
``expected_val=5``, ``units="V"``, and ``tolerance=0.5`` show intent at the call site.

``--dry-run`` does not call a decorated body unless that function opts in.
Pass ``dry_run="call"`` to run the real function, or ``dry_run=probe`` to call
``probe`` with the same arguments instead. The default, ``dry_run="log"``, logs
the arguments and returns ``None``.

.. code-block:: python

   @command(dry_run="call")
   def comment(*, message: str) -> None:
       _logger.info("%s", message)

   @command(dry_run=probe_idn)
   def open_instrument(*, address: str) -> None:
       ...

Decorators resolve the evidence domain when the function is defined. They
check its module, then walk parent packages for ``__colosseum_domain__``. Set
the package domain **before importing decorated APIs**, as the maintained
template does in its ``__init__.py``::

   __colosseum_domain__ = "template"
   from . import api

An API module can set its own domain before its decorated functions instead.
``register_namespace`` supplies a missing domain on the registered module,
but late registration does not change wrappers already created with the
fallback domain ``core``. A mismatched lookup then reports no measurement.

**colosseum_template/api.py** (excerpts)::

   from colosseum.decorators import VerificationResult, command, measurement, verification
   from colosseum.logging import get_logger

   _logger = get_logger("colosseum.template")
   __colosseum_domain__ = "template"

   @command
   def arm_device(*, device_id: int) -> None:
       from colosseum.context import get_context
       row = get_context().config.require_item("template.device", device_id)
       _logger.debug("arm_device device_id=%s serial=%s", device_id, row["serial"])

   @measurement
   def measure_widget_count(*, device_id: int, key: str) -> float:
       return float(device_id * 10)

   @verification
   def verify_widget_count(
       *, key: str, expected_val: float, tolerance: float = 0.0, optional: bool = False
   ) -> VerificationResult:
       from colosseum.context import get_context
       from colosseum.decorators import missing_measurement_result

       row = get_context().db.get_measurement(
           "template", "measure_widget_count", key, row_index=0
       )
       if row is None or row.value is None:
           return missing_measurement_result(key=key, optional=optional)
       actual = float(row.value)
       if abs(actual - expected_val) <= tolerance:
           return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
       return VerificationResult(
           status="FAIL",
           message=f"expected {expected_val} +/- {tolerance}, got {actual}",
           optional=optional,
           actual=actual,
       )

End users call these from test scripts (see :doc:`writing_test_scripts`)::

   col.template.arm_device(device_id=1)
   col.template.measure_widget_count(device_id=1, key="widgets")
   col.template.verify_widget_count(key="widgets", expected_val=10.0, tolerance=0.0)

Layer 2: Configuration
----------------------

Only plugins that own TOML sections need this. See :doc:`configuration` for load
behavior. Each ``ConfigSectionSpec`` is one table type:

* exactly one ``dotted_path``
* exactly one ``id_field`` (integer, unique per section)
* any number of ``required_keys`` and ``optional_keys`` (including none)

Register the spec in ``register()`` before ``register_namespace``::

   from colosseum.config.sections import ConfigSectionSpec

   registry.register_config_section(
       ConfigSectionSpec(
           dotted_path="template.device",
           id_field="device_id",
           required_keys=("serial",),
           optional_keys=("label",),
       )
   )
   registry.register_namespace("template", api)

Document matching rows for end users. Integer fields such as ``device_id`` and
``port`` must be TOML integers. **config.toml**::

   [template.device]
   device_id = 1
   serial = "TEMPLATE-001"
   # label = "optional field"

Unknown plugin-row keys are preserved without a core warning; a driver may
consume them or perform its own validation. Missing required keys raise when the
row is requested with ``require_item``. Document section keys and example rows in
your plugin README. See :doc:`configuration` for the full contract.

Layer 3: Resources and extras
-----------------------------

Optional registry hooks:

* ``registry.register_shutdown(callable)``: cleanup at process finalize (LIFO).
  On a single ``colosseum run``, that is ``col.endex()``. During
  ``colosseum run-suite``, hooks run once in ``finalize_suite`` after all slots;
  per-slot ``endex()`` closes ``resource_cache`` but does not run shutdown hooks.

Connection helpers (config lookup, cached resources on ``ctx.resource_cache``) are ordinary module functions,
not a framework decorator. I/O uses ordinary Python libraries or plugin drivers
(for example ``socket`` for UDP, or vendor stacks behind equipment/GUI plugins).
The template demo reads config inline; first-party plugins such as messaging and
equipment show cached-resource patterns.

If a measurement reflects a prior command's side effect, store the value in module
state in the command body and return it from the measurement, or compute it directly
in the measurement. Verifications always read prior rows from the database.

Logging
-------

Plugins log through ``colosseum.logging.get_logger`` with a name under the
``colosseum`` tree. ``setup_logging`` attaches the run file handler to the
``colosseum`` logger, so only that subtree is written to ``debug.log``::

   from colosseum.logging import get_logger

   _logger = get_logger("colosseum.template")

Use ``colosseum.<namespace>`` to match the registered namespace (``col.template`` maps
to ``colosseum.template``). Child loggers such as ``colosseum.template.api`` are fine.
Names like ``template`` or ``colosseum_template`` never reach ``debug.log``.

The file handler records DEBUG and above. Console output, when enabled, defaults
to INFO. Decorators already record command, measurement, and verification
pass/fail; do not duplicate that at INFO.

End-to-end checklist
--------------------

1. Copy ``examples/plugins/colosseum_template/`` and follow ``RENAME.md``.
2. Wire the entry point and ``register()`` (Layer 0).
3. Implement ``api.py`` with decorators (Layer 1) and optional ``ConfigSectionSpec`` (Layer 2).
4. ``pip install -e .`` in the same environment as ``colosseum-core``.
5. Run ``python examples/smoke_test.py`` or
   ``colosseum run examples/smoke_test.py --config configs/config.template.toml``.
6. Build a wheel with ``python -m build`` when ready to publish.

Files to document for end users
---------------------------------

Plugin authors should ship (or document) the same files shown in :doc:`writing_test_scripts`:

**config.toml** (plugin device rows)::

   [template.device]
   device_id = 1
   serial = "UNIT-001"

**metadata.yaml** (optional run identity)::

   test_metadata:
     location: TBD_PHYSICAL_LOCATION
     process_code: "1234"
     revision: "1.2.3"
     serial_number: "123"
     test_intent: Acceptance
     user_name: USERNAME
     uut: PARTNUMBER

**smoke_test.py** (consumer script)::

   import colosseum as col

   def main() -> None:
       col.config.load_config("config.toml")
       col.template.arm_device(device_id=1)
       col.template.measure_widget_count(device_id=1, key="widgets")
       col.template.verify_widget_count(key="widgets", expected_val=10.0, tolerance=0.0)

   if __name__ == "__main__":
       main()
       col.endex()

Troubleshooting
---------------

.. list-table::
   :header-rows: 1

   * - Symptom
     - Likely cause
   * - ``Namespace '…' is not registered``
     - Extension not installed in this environment
   * - ``Failed to load plugin entry point``
     - Exception inside ``register()``; see traceback
   * - ``Configuration is not loaded``
     - Call ``col.config.load_config(path)`` first
   * - Missing required keys
     - Config TOML row incomplete for your ``ConfigSectionSpec``
   * - ``Config section … is already registered``
     - Two plugins claim the same section
   * - ``AttributeError`` on ``col.yournamespace``
     - Typo in namespace or registration
   * - ``no measurement for key=…`` in verification
     - Evidence domain mismatch; set ``__colosseum_domain__`` on the API module and use
       the same domain in ``get_measurement(...)``

Documentation
-------------

Plugins document themselves (README and any project-local docs). Register
``colosseum.plugins`` only.
