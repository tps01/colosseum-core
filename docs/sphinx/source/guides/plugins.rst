Plugins and extensions
======================

Colosseum loads optional **plugins** at runtime via setuptools entry points. First-party
plugins ship with the main package (``colosseum_equipment``, ``colosseum_shared``,
``colosseum_host``). Third-party packages follow the same pattern.

When to build an extension
--------------------------

Build a separate extension when you need:

* A new instrument family or lab-specific glue that should not live in ``colosseum_equipment``.
* Customer- or site-specific bench helpers under your own namespace (e.g. ``col.acme``).
* Internal packages distributed outside the Colosseum monorepo.

Contribute to ``colosseum_equipment`` instead when the capability is a general-purpose
instrument driver useful across benches.

Package layout
--------------

Minimal tree (mirrors first-party plugins):

.. code-block:: text

   myvendor_bench/
     pyproject.toml
     myvendor_bench/__init__.py      # register(registry)
     myvendor_bench/api.py           # col.myvendor.* surface
     myvendor_bench/docgen_entry.py  # optional DocgenModuleSpec

A working reference skeleton lives at ``examples/plugins/myvendor_bench/``.

Step 1 — API module
-------------------

Export decorated functions from your API module. Use ``@command`` for setup/actions,
``@measurement`` for evidence capture, and ``@verification`` for checks. Import from
``colosseum.decorators``. Follow project script style: **one keyword argument per**
``col.*`` **call** in example and test scripts.

.. code-block:: python

   from colosseum.decorators import command, measurement, verification

   @command
   def arm_fixture(*, fixture_id: int) -> None:
       ...

   @measurement
   def measure_widget_count(*, fixture_id: int, key: str) -> float:
       ...

Step 2 — ``register(registry)``
-------------------------------

Implement ``register(registry: PluginRegistry)`` in ``__init__.py``:

* ``registry.register_namespace("myvendor", api)`` — exposes ``col.myvendor.*``
* ``registry.register_config_section(ConfigSectionSpec(...))`` — repeatable TOML tables
* ``registry.register_shutdown(callable)`` — optional cleanup (see ``colosseum_equipment``)

.. code-block:: python

   def register(registry: PluginRegistry) -> None:
       from myvendor_bench import api
       registry.register_namespace("myvendor", api)
       registry.register_config_section(
           ConfigSectionSpec(
               "myvendor.fixture",
               "fixture_id",
               required_keys=("serial",),
               optional_keys=("label",),
           )
       )

Step 3 — ``pyproject.toml`` entry points
----------------------------------------

.. code-block:: toml

   [project.entry-points."colosseum.plugins"]
   myvendor = "myvendor_bench:register"

   [project.entry-points."colosseum.docgen"]
   myvendor = "myvendor_bench.docgen_entry:spec"

Step 4 — Bench TOML
-------------------

Repeatable sections use array-of-tables syntax. Each row needs the section's ``id_field``
(integer):

.. code-block:: toml

   [[myvendor.fixture]]
   fixture_id = 1
   serial = "DEMO-001"

Unknown keys produce **warnings**; missing **required** keys raise errors at load time.

Step 5 — Install and verify
---------------------------

.. code-block:: powershell

   pip install -e .
   python -c "import colosseum as col; print(col.myvendor)"

Run a smoke script with ``col.config.load_config(...)``, your API calls, and ``col.endex()``.

Step 6 — Documentation
----------------------

Optional ``DocgenModuleSpec`` (see ``colosseum/docgen_spec.py``) registers API reference pages:

.. code-block:: python

   def spec() -> DocgenModuleSpec:
       return DocgenModuleSpec(
           module_id="myvendor_bench",
           title="My Vendor Bench",
           import_packages=["myvendor_bench"],
           autodoc_modules=["myvendor_bench"],
           order=50,
           namespace="myvendor",
       )

Build docs: ``python scripts/docgen/build_module.py`` or ``python scripts/docgen/build_all.py``.

Step 7 — Tests
--------------

* **Unit tests** — API logic and verifiers with ``unit_runtime_context``.
* **Integration** — ``ensure_plugins_loaded()`` and assert your namespace is registered
  (see ``tests/integration/test_plugin_registry_load.py``).

Collision and load order
------------------------

Namespace registration is **last-wins** (ADR-009). Avoid shadowing built-in namespaces:
``equipment``, ``shared``, ``io``, ``host``.

Monorepo development without install
------------------------------------

When Colosseum is run from a checkout without ``pip install -e .``, the core loader falls
back to built-in plugins (equipment, shared, host). **Third-party extensions still require**
``pip install -e .`` so their entry points are visible.

Runtime API (today)
-------------------

Plugins register via entry points only. ``register_module()`` and ordered ``load_all()``
described in archived ADR-002 are **not** implemented; do not rely on them.

See also
--------

* :doc:`host_environment` — bundled ``col.host`` bench-PC checks
* :doc:`quickstart` — first test script
* ``examples/plugins/myvendor_bench/`` — copy-pasteable skeleton
