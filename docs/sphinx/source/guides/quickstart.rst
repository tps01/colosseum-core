Quickstart
==========

This page assumes you already installed core (and any plugins you need) from a
GitHub Release wheel into a virtual environment. See :doc:`installation` if
``colosseum`` is not on your ``PATH``.

1. Confirm the install
----------------------

::

   colosseum --help

2. Minimal script
-----------------

Colosseum test cases are ordinary Python scripts that call
``col.<namespace>.*`` APIs from installed plugins. When you launch with
``colosseum run``, the runner calls ``main()`` and finalizes the slot when the
script returns (you do not need ``col.endex()`` under the CLI).

**my_test.py**::

   import colosseum as col

   def main() -> None:
       # Replace with calls from installed plugins, for example:
       # col.shared.wait.wait_seconds(seconds=0.1)
       pass

3. Minimal config
-----------------

Plugins declare the TOML tables they own. A tiny shared-only smoke config can be
empty of instrument rows; equipment benches need section rows such as
``[[equipment.psu]]``. Example placeholder::

   # config.toml — add plugin sections as required by your script
   [colosseum.reports]
   wats = false
   junit = false

4. Run
------

::

   colosseum run my_test.py -g config.toml

Artifacts land under ``outputs/<timestamp>_my_test-pass/`` (or ``-fail``):
``debug.log``, ``execution.sqlite``, ``summary.txt``, and ``summary.json``.
Optional WATS or JUnit files appear only when you enable them
(``--report wats``, ``--report junit``, or ``[colosseum.reports]``). See
:doc:`output_artifacts`.

5. Next steps
-------------

* Ready-made procedures to copy into a project: :doc:`testware_library`.
* Full script + metadata walkthrough: :doc:`writing_test_scripts`.
* CLI flags and execution modes: :doc:`running_tests`.
* Suites: :doc:`running_suites`.
* First-party plugins (config → procedure → verify): :doc:`first_party_plugins`.
* Extension authors: :doc:`plugins`.
