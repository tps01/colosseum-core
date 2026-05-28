Plugin development
==================

Extensions use the same entry points as first-party packages.

**Runtime plugins** (``colosseum.plugins``)::

   def register(registry):
       registry.register_namespace("myvendor", myvendor.api)
       registry.register_config_section(
           ConfigSectionSpec("myvendor.fixture", "fixture_id", required_keys=("serial",))
       )

**Documentation** (``colosseum.docgen``) — return a ``DocgenModuleSpec`` from ``colosseum.docgen_spec``::

   # myvendor/docgen_entry.py
   from colosseum.docgen_spec import DocgenModuleSpec

   def spec():
       return DocgenModuleSpec(
           module_id="myvendor_bench",
           title="My Vendor Bench",
           import_packages=["myvendor_bench"],
           autodoc_modules=["myvendor_bench"],
           order=50,
           namespace="myvendor",
       )

In ``pyproject.toml``::

   [project.entry-points."colosseum.plugins"]
   myvendor = "myvendor_bench:register"

   [project.entry-points."colosseum.docgen"]
   myvendor = "myvendor_bench.docgen_entry:spec"

After packaging, the same ``scripts/docgen/build_module.py`` and ``build_all.py`` used for core will pick up your entry point.
