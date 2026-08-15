Plugins and extensions
======================

Colosseum loads optional **plugins** at runtime via setuptools entry points. First-party
plugins ship with the main package (``colosseum_equipment``, ``colosseum_shared``,
``colosseum_host``). Third-party packages follow the same pattern.

**Step-by-step author and end-user instructions** live in the extension template README:
``examples/plugins/colosseum_template/README.md``.

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

   colosseum_template/
     pyproject.toml
     README.md
     colosseum_template/__init__.py   # register(registry)
     colosseum_template/api.py        # col.template.* surface
     colosseum_template/docgen_entry.py  # optional DocgenModuleSpec

Copy and customize ``examples/plugins/colosseum_template/`` (see ``RENAME.md`` in that directory).

Step 1 — API module
-------------------

Export decorated functions from your API module. Use ``@command`` for setup/actions,
``@measurement`` for evidence capture, and ``@verification`` for checks. Import from
``colosseum.decorators``. Follow project script style: **one keyword argument per**
``col.*`` **call** in example and test scripts.

.. code-block:: python

   from colosseum.decorators import command, measurement, verification

   @command
   def arm_device(*, device_id: int) -> None:
       ...

   @measurement
   def measure_widget_count(*, device_id: int, key: str) -> float:
       ...

Step 2 — ``register(registry)``
-------------------------------

Implement ``register(registry: PluginRegistry)`` in ``__init__.py``:

* ``registry.register_namespace("template", api)`` — exposes ``col.template.*`` (rename when forking)
* ``registry.register_config_section(ConfigSectionSpec(...))`` — repeatable TOML tables
* ``registry.register_shutdown(callable)`` — optional cleanup (see ``colosseum_equipment``)

.. code-block:: python

   def register(registry: PluginRegistry) -> None:
       from colosseum_template import api
       registry.register_namespace("template", api)
       registry.register_config_section(
           ConfigSectionSpec(
               "template.device",
               "device_id",
               required_keys=("serial",),
               optional_keys=("label",),
           )
       )

Step 3 — ``pyproject.toml`` entry points
----------------------------------------

.. code-block:: toml

   [project.entry-points."colosseum.plugins"]
   template = "colosseum_template:register"

   [project.entry-points."colosseum.docgen"]
   template = "colosseum_template.docgen_entry:spec"

Step 4 — Bench TOML
-------------------

Repeatable sections use array-of-tables syntax. Each row needs the section's ``id_field``
(integer):

.. code-block:: toml

   [[template.device]]
   device_id = 1
   serial = "TEMPLATE-001"

Unknown keys produce **warnings**; missing **required** keys raise errors at load time.

Step 5 — Install and verify
---------------------------

.. code-block:: powershell

   pip install -e .
   python -c "import colosseum as col; col.config.load_config('configs/bench.template.toml'); print(col.template)"

Third-party namespaces use ``col.<namespace>`` via module ``__getattr__`` (Colosseum >= 0.14.0).
Run ``examples/smoke_test.py`` or ``colosseum run ... --config ...`` with ``col.endex()`` at the end of test scripts.

Step 6 — Documentation
----------------------

Optional ``DocgenModuleSpec`` (see ``colosseum/docgen_spec.py``) registers API reference pages:

.. code-block:: python

   def spec() -> DocgenModuleSpec:
       return DocgenModuleSpec(
           module_id="colosseum_template",
           title="Colosseum Template Extension",
           import_packages=["colosseum_template"],
           autodoc_modules=["colosseum_template"],
           order=50,
           namespace="template",
       )

Build docs: ``python scripts/docgen/build_module.py`` or ``python scripts/docgen/build_all.py``.

Step 7 — Tests
--------------

The template stub does not ship tests. Extension authors may add their own:

* **Unit tests** — API logic and verifiers with ``unit_runtime_context``.
* **Integration** — ``ensure_plugins_loaded()`` and assert your namespace is registered
  (see ``tests/integration/test_plugin_registry_load.py``).

Collision and load order
------------------------

Duplicate namespace or config section registration raises ``PluginRegistrationError``
(fail-fast). Avoid shadowing built-in namespaces: ``equipment``, ``shared``, ``io``, ``host``.

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
* ``examples/plugins/colosseum_template/README.md`` — author and end-user workflow
