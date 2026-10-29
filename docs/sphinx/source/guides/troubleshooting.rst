Troubleshooting
===============

Start with the failed run's ``summary.txt`` and ``debug.log``. In a suite,
inspect the individual slot folder as well as the container summary.

.. list-table::
   :header-rows: 1

   * - Symptom
     - Check
   * - ``col.equipment`` (or another namespace) is unavailable
     - Install that plugin in the same interpreter as core. Run the discovery
       command below; check startup errors in ``debug.log``.
   * - VISA instrument is not detected
     - Confirm the system VISA backend, resource string, cable/network access,
       and identity/driver match. See Equipment's transport guide.
   * - A verifier cannot find a key
     - Check domain, command, key, and row index in ``measurements``. Instrument
       IDs are not measurement identity. See :doc:`measurements_verifications`.
   * - GUI element is missing
     - Check the active window/page, locator type and driver capabilities.
       Capture the tree and screenshot; see the GUI driver/locator guide.
   * - SSH operation times out
     - Connection timeout/retries and command/collection timeout are independent.
       A timed-out command is not evidence that the remote process stopped.
   * - Suite passes after setup failed
     - Supporting slots do not fail the suite with ``fail_fast=false``.
       See :doc:`running_suites`.
   * - A report is absent
     - Enable ``--report junit`` or ``--report wats``. Metadata alone does not
       enable reports; supporting suite slots do not write them.
   * - Config reload has no effect
     - CLI ``-g`` pins config. Use ``force=True`` for an intentional replacement;
       see :doc:`configuration`.

Inspect installed plugins
-------------------------

Run with the Python interpreter used for your tests::

   python -c "from importlib.metadata import entry_points; print([(ep.name, ep.value) for ep in entry_points(group='colosseum.plugins')])"
   python -m pip show colosseum-core colosseum-equipment

Entry points show installed plugin registrations. The namespace used in a
script is the one the plugin registers (Equipment registers both ``equipment``
and ``io``). Distribution presence alone does not prove registration succeeded;
inspect startup exceptions if a listed plugin does not load.

Windows paths with spaces
-------------------------

For ``--use-previous-output`` and other CLI paths, omit a trailing backslash
before a closing quote. Windows native argument parsing can combine it with
the quote and produce ``unrecognized arguments``. Use either form::

   colosseum run my_test.py -g config.toml -u "D:\runs\prior run"
   colosseum run my_test.py -g config.toml -u "D:/runs/prior run/"

Plugin-specific diagnostics
---------------------------

* `Equipment transports and selection <https://tps01.github.io/colosseum-equipment/guides/transports_support.html>`__
* `Messaging protocol failures <https://tps01.github.io/colosseum-messaging/guides/protocol_workflows.html>`__
* `GUI driver capabilities and locators <https://tps01.github.io/colosseum-gui/guides/drivers_locators.html>`__
* `Host platform matrix <https://tps01.github.io/colosseum-host/readme.html#platform-capability>`__
