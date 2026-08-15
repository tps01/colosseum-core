Configuration
=============

Core reads TOML and lets installed plugins declare the sections they own. A repeatable
plugin section uses an array of tables::

   [[acme.device]]
   device_id = 1
   resource = "SIM::1"

Each plugin registers a ``ConfigSectionSpec`` containing its dotted section path, integer
ID field, required keys, and optional keys. Missing required values and duplicate IDs are
errors; unknown keys produce warnings.

Load configuration before calling plugin APIs::

   import colosseum as col

   col.config.load_config("bench.toml")

Plain string tokens may omit quotes when they contain only supported path/token
characters. Standard TOML quoting remains recommended for portable configuration.

The generated :doc:`bench_config_reference` lists sections provided by the plugins
installed in the documentation build environment. A core-only build therefore contains
no plugin sections.
