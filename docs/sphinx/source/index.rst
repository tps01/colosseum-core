Colosseum
=========

A Python test automation framework for hardware and software testing.

This site is the **documentation hub** for Colosseum core. Install from GitHub
Release wheels. First-party plugins publish their own
GitHub Pages sites (linked below). Copy-out test stubs live in the
`colosseum-library <https://github.com/tps01/colosseum-library>`__ catalog; see
:doc:`guides/testware_library`.

How Colosseum works
-------------------

Colosseum runs Python test scripts that call plugins to control equipment,
communicate with devices, collect measurements, and verify results. A script's
``main()`` contains the procedure. The runner initializes the framework,
executes that procedure, records evidence, and generates a result summary.

With Shared installed, a procedure can record and check a literal value::

   import colosseum as col

   def main() -> None:
       col.shared.measure_value(key="voltage", value=3.3)
       col.shared.verify.verify_field(key="voltage", expected_val=3.3, tolerance=0.1)

See :doc:`guides/quickstart` for the complete runnable example. Scripts run
individually or in suites. The **desktop runner** (``colosseum --gui``) lets
operators launch and monitor tests. The **GUI automation plugin** instead
controls the application under test through ``col.gui.*``.

.. toctree::
   :maxdepth: 1
   :caption: Getting started

   guides/installation
   guides/quickstart
   guides/writing_test_scripts

.. toctree::
   :maxdepth: 1
   :caption: User guide

   guides/configuration
   guides/using_parameters
   guides/measurements_verifications
   guides/running_tests
   guides/running_suites
   guides/output_artifacts

.. toctree::
   :maxdepth: 1
   :caption: Plugins and examples

   guides/first_party_plugins
   guides/testware_library

.. toctree::
   :maxdepth: 1
   :caption: Reference and troubleshooting

   guides/exit_codes
   guides/glossary
   guides/platform_notes
   guides/troubleshooting

.. toctree::
   :maxdepth: 1
   :caption: Development

   guides/runtime_execution
   guides/plugins
   guides/implementing_evidence
   guides/configuration_schema
   guides/python_imports

First-party plugins
-------------------

Choose APIs by task in :doc:`guides/first_party_plugins`. Each plugin site
contains getting-started guides, workflows, configuration, and API reference.

* `colosseum-equipment <https://tps01.github.io/colosseum-equipment/>`__ —
  instruments and I/O (`col.equipment.*`, `col.io.*`) —
  `GitHub <https://github.com/tps01/colosseum-equipment>`__
* `colosseum-gui <https://tps01.github.io/colosseum-gui/>`__ —
  product UI automation (`col.gui.*`) —
  `GitHub <https://github.com/tps01/colosseum-gui>`__
* `colosseum-host <https://tps01.github.io/colosseum-host/>`__ —
  local host prerequisites and telemetry (`col.host.*`) —
  `GitHub <https://github.com/tps01/colosseum-host>`__
* `colosseum-messaging <https://tps01.github.io/colosseum-messaging/>`__ —
  HTTP, Redis, ZMQ, MQTT, SSH, SCP (`col.messaging.*`) —
  `GitHub <https://github.com/tps01/colosseum-messaging>`__
* `colosseum-shared <https://tps01.github.io/colosseum-shared/>`__ —
  wait, measure, verify, regex, parsing, prompts (`col.shared.*`) —
  `GitHub <https://github.com/tps01/colosseum-shared>`__
