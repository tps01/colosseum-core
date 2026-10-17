Colosseum
=========

A Python test automation framework for hardware and software testing.

This site is the **documentation hub** for Colosseum core. First-party plugins
publish their own GitHub Pages sites (linked below). The copy-out testware
library is not documented here yet.

.. toctree::
   :maxdepth: 2
   :caption: User guide

   guides/installation
   guides/quickstart
   guides/running_tests
   guides/writing_test_scripts
   guides/configuration
   guides/running_suites
   guides/measurements_verifications
   guides/output_artifacts
   guides/exit_codes
   guides/platform_notes

.. toctree::
   :maxdepth: 2
   :caption: Developing

   guides/runtime_execution
   guides/plugins
   guides/glossary

First-party plugins
-------------------

Each plugin site is an **API reference** for that package's ``col.*`` surface.
Return here for framework guides (install, config, runners, plugins).

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
