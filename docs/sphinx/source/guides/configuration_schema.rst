Plugin configuration schemas
============================

For configuring a bench, start with :doc:`configuration`. This page is for
plugin authors registering and reading sections.

Configuration sections
----------------------

Each registered section is one ``ConfigSectionSpec``:

* exactly one dotted path (the TOML table, for example ``template.device``)
* exactly one integer ID field (the row identity, for example ``device_id``)
* any number of required keys (including none)
* any number of optional keys (including none)

A plugin that owns several table types registers several specs, one
``register_config_section`` call per dotted path. The same file can mix sections
from many plugins.

Reading rows
------------

* ``col.config.get("template.device")``: raw nested table or list (or ``None``).
* ``store.list_items("template.device")``: normalized rows, sorted by ID.
* ``store.get_item("template.device", 1)`` / ``store.require_item(...)``: one row
  by ID. ``require_item`` also checks required keys.

Unregistered tables stay in the raw store (``col.config.get("runtime.label")``)
but are not ID-indexed.


See :doc:`plugins` for registration examples.
