Configuration
=============

Core reads one TOML config file. Installed plugins declare the sections they own.
Core itself does not define domain-specific keys (instruments, UI targets,
services, and so on).

The :doc:`writing_test_scripts` walkthrough uses a ``[template.device]`` table from the
``colosseum_template`` plugin. The rules below apply to any plugin section.

TOML shape
----------

Write either a single table (one row) or an array of tables (several rows).
Do not mix both for the same dotted path. Both forms are accepted by the configuration loader.

Single row::

   [template.device]
   device_id = 1
   serial = "TEMPLATE-001"

Several rows::

   [[template.device]]
   device_id = 1
   serial = "TEMPLATE-001"

   [[template.device]]
   device_id = 2
   serial = "TEMPLATE-002"

The dotted path is the table header. The ID field must be an integer and unique
within that section. Missing IDs, non-integer IDs, and duplicate IDs fail the
load. Missing required keys fail when the plugin requests that row. Plugin-row keys outside the registered spec are currently
preserved and passed through without a core warning; plugins may consume
extension data or validate it themselves. Do not rely on core to detect a
misspelled plugin key. Metadata and report tables have separate validation.

IDs in calls
------------

``device_id=2`` selects row 2 of ``template.device``. IDs belong to their own
section: PSU 1 and DMM 1 can coexist. Select a configured ID, not a row number
in the text file. See each plugin's configuration reference for its ID fields.

A typo such as ``resouce = "COM5"`` is preserved as an unknown plugin key by
core. It does not satisfy a plugin's required ``resource`` field. Core checks
table shape and IDs; the plugin checks its required fields and capabilities.

Load configuration
------------------

Load configuration before calling plugin APIs::

   import colosseum as col

   col.config.load_config("config.toml")

or ``colosseum run my_test.py -g config.toml`` (``-g`` is the legacy short form of
``--config``). That discovers plugins, normalizes registered sections, then attaches a
config store to the run. CLI ``-g`` **pins** that store: a later script
``load_config`` is ignored unless you pass ``force=True``.

Calling ``load_config`` again (unpinned, or with ``force=True``) replaces the
whole store. Sections present only in the previous file are dropped unless the
new TOML includes them.

Reload scenarios
----------------

With ``colosseum run my_test.py -g bench.toml``, the CLI pins the configuration.
Inside ``main()``::

   col.config.load_config("other.toml")              # ignored; bench.toml stays active
   col.config.load_config("other.toml", force=True)  # replaces bench.toml

Without a CLI pin, loading a second file replaces the first::

   col.config.load_config("bench.toml")
   col.config.load_config("other.toml")  # other.toml is now the entire store

Rows present only in ``bench.toml`` disappear. A reload closes cached resources;
later calls reopen connections from the active configuration. The same
``force=True`` rule applies independently to CLI-pinned metadata.

Relative file paths
-------------------

Script calls to ``load_config`` and ``load_metadata`` look in the working
directory first, then relative to the executing test/setup/teardown script.
For example, ``load_config("../config.toml")`` can load the file above the test
script when it is absent at the working-directory-relative location. The same
rule applies to ``load_config(..., metadata_path="metadata.yaml")`` and direct
``python script.py`` runs. If both locations exist, the working-directory file
wins. Use an absolute path (for example one built from ``__file__``) to select
one file explicitly. A parse error in the selected file is reported immediately.
Missing-file errors list the attempted paths.

CLI ``-g`` / ``-m`` paths remain relative to the working directory. Pinned script
loads are ignored before checking any paths; ``force=True`` enables resolution
and replacement. Paths stored *inside* config files keep their existing semantics.

Plain string tokens may omit quotes when they contain only supported path/token
characters. Standard TOML quoting remains recommended for portable configuration.

Standard TOML uses lowercase ``true`` and ``false``. Use those spellings in
portable configuration files. Colosseum also accepts extensions for recognized
boolean fields; these spellings are not standard TOML syntax.

Boolean fields accept ``true``, ``t``, ``yes``, ``y``, and ``1``, and ``false``,
``f``, ``no``, ``n``, and ``0``, in any case. Bare words such as ``True`` and
``T`` are included. The same spellings apply in suite files and parameters
files. Unquoted ``1`` and ``0`` stay numbers. Boolean fields such as
``[colosseum.reports]`` and ``fail_fast`` also accept those numbers.

Suite TOML (``colosseum run-suite``) lists scripts. It is not a plugin section
file; pass config separately with ``--config``.

Run metadata (``[colosseum.metadata]``)
---------------------------------------

Core owns a flat singleton table for test-report identity fields. It is **not**
a plugin ``ConfigSectionSpec`` (no integer ID field). Unknown keys produce
warnings.

::

   [colosseum.metadata]
   location = "TBD_PHYSICAL_LOCATION"
   process_code = "1234"
   revision = "1.2.3"
   serial_number = "123"
   test_intent = "Acceptance"
   user_name = "USERNAME"
   uut = "PARTNUMBER"
   # wats_folder = "D:/wats/inbox"   # optional copy destination

The same keys may appear in a metadata YAML file (``test_metadata:`` block).
Load YAML with ``col.config.load_metadata("metadata.yaml")`` or
``colosseum run my_test.py -m metadata.yaml`` (``-m`` is the short form of
``--metadata``). CLI ``-m`` **pins** that YAML: a later script
``load_metadata`` is ignored unless you pass ``force=True``.

Metadata precedence
~~~~~~~~~~~~~~~~~~~

1. Values from ``[colosseum.metadata]`` in config TOML (if present).
2. YAML ``test_metadata`` overrides TOML when both are loaded (CLI ``-m`` wins
   over a script ``load_metadata`` unless ``force=True``).
3. Runtime defaults (hostname, OS user, empty identity fields) fill any remaining gaps.

When the ``wats`` report listener is enabled, finalize writes
``wats_<datetime>_<script>.json`` beside ``summary.json`` (see
:doc:`output_artifacts`). Without metadata, Colosseum still builds that report
using runtime defaults. ``wats_folder`` is consulted only when WATS is enabled.

Optional keys (never required) may enrich the report when set in YAML:
``process_name``, ``report_text``, ``seq_version``, ``batch_serial``,
``fixture_id``, ``comment``, ``misc_infos``, and ``sub_units``. Existing
metadata files without these keys continue to work unchanged.

Report listeners (``[colosseum.reports]``)
------------------------------------------

Core owns a boolean table for opt-in report formats. Report choice is run
configuration, not unit identity (do not put these flags in metadata)::

   [colosseum.reports]
   wats = false
   junit = false

Use standard TOML ``wats = true`` and ``junit = false``.
Both default to false when the table is absent. CLI ``--report NAME``
(repeatable) replaces the table for that process. An unknown name warns and
does not fail the run. See :doc:`output_artifacts`.

.. figure:: ../_static/uml/config-priority.png
   :alt: Precedence for config, metadata, reports, and execution mode
   :align: center

   CLI pins and ``--report`` override script loads and the reports table.

Plugin-owned config sections are documented by each plugin (README or project
docs). For first-party setup recipes, see :doc:`first_party_plugins`.

Plugin developers: :doc:`configuration_schema` documents registration and the
normalized store API.
