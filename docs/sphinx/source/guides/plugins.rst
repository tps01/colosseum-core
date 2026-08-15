Plugins and extensions
======================

Plugins are separate Python distributions discovered from setuptools entry points.
The copy-ready template is under ``examples/plugins/colosseum_template``.

Runtime registration
--------------------

A plugin exposes a registration callable::

   from colosseum.config.sections import ConfigSectionSpec

   def register(registry):
       from acme_plugin import api

       registry.register_namespace("acme", api)
       registry.register_config_section(
           ConfigSectionSpec(
               dotted_path="acme.device",
               id_field="device_id",
               required_keys=("resource",),
           )
       )

Declare it in ``pyproject.toml``::

   [project.entry-points."colosseum.plugins"]
   acme = "acme_plugin:register"

The namespace becomes ``col.acme`` after the distribution is installed. Duplicate
namespaces or config sections raise ``PluginRegistrationError``.

Decorated APIs
--------------

Plugin API functions use ``command``, ``measurement``, and ``verification`` from
``colosseum.decorators``. Set ``__colosseum_domain__`` on the package when evidence
should use a domain other than ``core``.

Shutdown hooks registered with ``registry.register_shutdown`` run in reverse order when
``col.endex()`` finalizes the runtime.

Documentation
-------------

Plugins may expose a ``colosseum.docgen`` entry point returning ``DocgenModuleSpec``.
Core documentation discovers those modules only when their distributions are installed.

Source checkouts do not provide entry-point metadata. Use ``pip install -e .`` while
developing a plugin.
