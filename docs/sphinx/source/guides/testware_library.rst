Testware library
================

The
`colosseum-library <https://github.com/tps01/colosseum-library>`__
repository is a catalog of **copy-out example test stubs**. It is not a pip
package and does not register a ``col.library`` namespace. You copy a folder into
your project, fill ``FILL_IN_HERE``, wire config, and run with ``colosseum``.

Install core and the plugins named in each stub's docstring from GitHub Release
wheels first (:doc:`installation`).

Recommended first copies
------------------------

.. list-table::
   :header-rows: 1

   * - Stub
     - Notes
   * - ``power/rail_voltage/``
     - PSU + DMM measure → verify; optional ``parameters.toml`` for limits
   * - ``digital/gpio/``
     - DIO bring-up
   * - ``host/bench_prerequisites/``
     - Bench-PC checks (good early smoke)
   * - ``suites/power_acceptance.toml.example``
     - Suite pointing at the rail stub (optional ``parameters=``)

Layout
------

* ``power/``, ``digital/``, ``rf/``, ``host/``, ``gui/`` — domain catalogs
* ``suites/`` — TOML templates that compose blocks (paths relative to the suite)
* ``_template/`` — checklist when adding a new catalog test

Each topic folder typically includes ``test_*.py``, ``README.md``,
``config.toml.example``, and sometimes ``parameters.toml.example``.

How to use a stub
-----------------

1. Copy the topic directory into your project.
2. Replace every ``FILL_IN_HERE`` in the script (units are in trailing comments).
3. Wire instruments: leave ``USE_AUTOCONFIG = True`` for VISA discovery, or copy
   ``config.toml.example`` → ``config.toml`` and set ``USE_AUTOCONFIG = False``.
4. Optionally copy ``parameters.toml.example`` → ``parameters.toml`` (or pass
   ``--parameters`` / suite ``parameters=``).
5. Run::

      colosseum run path/to/test_rail_voltage.py --config config.toml
      colosseum run path/to/test_rail_voltage.py --config config.toml --parameters parameters.toml --report junit

Showcase: rail voltage
----------------------

After copy-out, the procedure looks like this (IDs and setpoints still
``FILL_IN_HERE`` in the catalog)::

   def main() -> None:
       _load_bench()
       col.equipment.psu.set_voltage(psu_id=psu_id, voltage=set_voltage_v)
       col.equipment.psu.set_current_limit(psu_id=psu_id, current=current_limit_a)
       col.equipment.psu.set_output(psu_id=psu_id, enabled=True)
       col.equipment.dmm.measure_voltage(dmm_id=dmm_id, channel=dmm_channel, key="rail_v")
       col.equipment.dmm.verify_voltage(
           key="rail_v",
           expected_val=expected_voltage_v,
           tolerance=voltage_tolerance_v,
       )

Optional limits file (``parameters.toml.example``)::

   [rail_v]
   expected_val = 3.3
   tolerance = 0.1

Suite composition (``suites/power_acceptance.toml.example``)::

   name = "power_acceptance"
   tests = [
     { path = "../power/rail_voltage/test_rail_voltage.py",
       parameters = "../power/rail_voltage/parameters.toml.example" },
   ]

See also :doc:`writing_test_scripts` (parameters), :doc:`running_suites`, and
:doc:`first_party_plugins`.
