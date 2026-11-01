Writing test scripts
====================

Colosseum test cases are ordinary Python scripts. Installed plugins expose APIs
as ``col.<namespace>.*``. This chapter walks through a complete script with matching
config TOML and metadata YAML. The template plugin below is a developer example,
not a separately published package. From the core repository, install it with
``python -m pip install -e examples/plugins/colosseum_template``. For a first test
using a released plugin, follow :doc:`quickstart`.

Recommended project layout
--------------------------

Organize files so suite paths stay relative to the suite file::

   my_project/
     config/
       config.toml
       metadata.yaml
     scripts/
       my_test.py
     suites/
       smoke.toml

Suite script paths are relative to the suite TOML file (for example
``../scripts/my_test.py``). Config and metadata paths are passed on the CLI or
loaded from your script.

Script anatomy
--------------

A measurement key identifies a recorded result. A verification uses that key
to retrieve the measurement and compare it with its expected value. See
:doc:`measurements_verifications` for identity and lookup rules.

Every test script follows the same shape:

1. ``import colosseum as col``
2. Load config (and optional metadata) before calling plugin APIs when running
   with ``python my_test.py``. The CLI loads ``--config`` and ``--metadata`` for you.
3. Call plugin APIs in ``main()`` (one ``col.*`` call per line, keyword arguments inline).
   Decorated APIs use keyword arguments so scripts stay readable to people less
   familiar with Python: values such as ``expected_val=5``, ``units="V"``, and
   ``tolerance=0.5`` make the test intent obvious on inspection.
4. Call ``col.endex()`` when running with ``python my_test.py``. The CLI finalizes the
   slot automatically when ``main()`` returns.

CLI skeleton (``colosseum run`` loads config and metadata from flags)::

   import colosseum as col

   def main() -> None:
       col.template.arm_device(device_id=1)
       col.template.measure_widget_count(device_id=1, key="widgets")
       col.template.verify_widget_count(key="widgets", expected_val=10.0, tolerance=0.0)

Omit ``load_config`` / ``load_metadata`` under the CLI: ``-g`` and ``-m`` pin
those values. A leftover script ``load_config`` / ``load_metadata`` is ignored
(warn once) unless you pass ``force=True`` for an intentional reload.

Direct-Python skeleton (script loads config and calls ``endex()``)::

   import colosseum as col

   def main() -> None:
       col.config.load_config("config/config.toml")
       col.config.load_metadata("config/metadata.yaml")  # optional
       col.template.arm_device(device_id=1)
       col.template.measure_widget_count(device_id=1, key="widgets")
       col.template.verify_widget_count(key="widgets", expected_val=10.0, tolerance=0.0)

   if __name__ == "__main__":
       main()
       col.endex()

File and log checks that do not look evidence up by key can omit ``key=`` on
``@verification`` calls; the decorator warns in ``debug.log`` and still runs
the body. Call ``col.auto_key()`` at the top of ``main()`` (after
``load_config`` when the script starts the runtime) when omitted measurement
or verification keys should be numbered ``"1"``, ``"2"``, and so on instead.
See :doc:`measurements_verifications`.

When you run through the CLI, the runner does not execute the script's
``if __name__ == "__main__"`` block. It calls ``main()`` and finalizes the slot
automatically if the script returns without calling ``endex()``.

For shared helpers and module-name collisions, see :doc:`python_imports`.

Relative ``load_config`` / ``load_metadata`` paths try the process working
directory first, then the directory of the executing script. Prefer paths
relative to ``Path(__file__).resolve().parent`` for other assets (for example
``open("data.csv")``), which still use the process working directory unless you
resolve them yourself.

``colosseum run`` can start without an in-script ``load_config`` (CLI ``-g``).
Direct ``python script.py`` needs ``load_config`` (or equivalent) before
decorators / ``endex``.

Configuration
-------------

Config TOML describes plugin-owned rows (instruments, hosts, UI targets,
services, and whatever else installed plugins register).
Load it before any ``col.*`` API call::

   col.config.load_config("config.toml")

or pass ``--config config.toml`` to ``colosseum run``.

The example below uses the ``colosseum_template`` plugin (namespace ``template``).
A ``[template.device]`` table matches that plugin's ``ConfigSectionSpec``:

**config.toml**::

   [template.device]
   device_id = 1
   serial = "TEMPLATE-001"
   # label = "optional field"

See :doc:`configuration` for section rules, multiple rows, and reading rows from code.

Parameters (optional)
---------------------

A parameters TOML file supplies command arguments and verification limits by
evidence key. See :doc:`using_parameters` for precedence, a worked limit change,
and parameter export.

Metadata (optional)
-------------------

Metadata identifies the unit under test and the test run. It is optional.
WATS and JUnit reports are opt-in listeners (see :doc:`output_artifacts`);
metadata enriches WATS identity fields when that report is enabled.

Provide metadata in one of two ways:

* A ``[colosseum.metadata]`` table in config TOML (see :doc:`configuration`).
* A YAML file loaded with ``col.config.load_metadata("metadata.yaml")`` or
  ``--metadata metadata.yaml``.

YAML overrides the TOML table when both are present.

**metadata.yaml**::

   test_metadata:
     location: TBD_PHYSICAL_LOCATION
     process_code: "1234"
     revision: "1.2.3"
     serial_number: "123"
     test_intent: Acceptance
     user_name: USERNAME
     uut: PARTNUMBER
     # wats_folder: "D:/wats/inbox"   # optional copy destination

Optional keys such as ``process_name``, ``report_text``, ``seq_version``,
``batch_serial``, ``fixture_id``, ``comment``, ``misc_infos``, and ``sub_units`` may
enrich the report. Existing metadata files without these keys continue to work.

Full worked example
-------------------

The files below describe one test run.

**scripts/my_test.py** (CLI variant)::

   import colosseum as col

   def main() -> None:
       col.template.arm_device(device_id=1)
       col.template.measure_widget_count(device_id=1, key="widgets")
       col.template.verify_widget_count(
           key="widgets", expected_val=10.0, tolerance=0.0
       )

**config/config.toml**::

   [template.device]
   device_id = 1
   serial = "TEMPLATE-001"

**config/metadata.yaml**::

   test_metadata:
     location: TBD_PHYSICAL_LOCATION
     process_code: "1234"
     revision: "1.2.3"
     serial_number: "123"
     test_intent: Acceptance
     user_name: USERNAME
     uut: PARTNUMBER

Running the script
------------------

CLI (recommended; loads config and metadata from flags)::

   colosseum run scripts/my_test.py -g config/config.toml -m config/metadata.yaml

See :doc:`running_tests` for ``-i``, ``-o``, ``-c``, ``-p``, ``-u``, and other CLI
options.

Direct execution (add ``load_config``, ``load_metadata``, and ``col.endex()`` as in the
Direct-Python skeleton above)::

   python scripts/my_test.py

When WATS is enabled and metadata is omitted, the report still builds using
runtime defaults (hostname, OS user, empty identity fields). See
:doc:`output_artifacts`.

Utility scripts
---------------

When you do not need persisted evidence (no ``outputs/`` directory), load config with
``no_artifacts=True`` or pass ``--no-artifacts`` on the CLI::

   col.config.load_config("config.toml", no_artifacts=True)

   # or
   colosseum run my_test.py --config config.toml --no-artifacts

Extension authors should read :doc:`plugins`. For suite orchestration, see
:doc:`running_suites`.
