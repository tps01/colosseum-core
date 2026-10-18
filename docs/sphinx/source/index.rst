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

Colosseum is meant to stay approachable for people who are not primarily
software developers, without capping what experienced authors can do.

**Readable procedures.** Plugin APIs use keyword arguments at the call site
(``expected_val=5``, ``units="V"``, ``tolerance=0.5``). Named steps make the
intent obvious on the page, so reviewers who do not write code can still follow
a procedure as a checklist. A typical case is a short, straight-line sequence of
``col.*`` calls.

**Operator desktop GUI.** Users who only need to select a script or suite,
attach config and metadata, and start a run can do that from the desktop GUI
(``colosseum --gui``) without editing Python. Completed runs are browsable from
the same app through summaries and logs.

**Room for advanced cases.** The same scripts are ordinary Python, so authors
can use loops, variables, conditionals, helpers, and third-party libraries when
a scenario needs them. Parameters files and suite definitions support
parameterized limits and multi-slot campaigns without inventing a separate test
language. Evidence recording (commands, measurements, and verifications) wraps
those calls; see :doc:`guides/writing_test_scripts` and
:doc:`guides/measurements_verifications`.

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
   guides/first_party_plugins
   guides/testware_library
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
