Quickstart
==========

Run a single test with the simulated bench configuration (no hardware)::

   set COLOSSEUM_BENCH_CONFIG=bench.sim.toml
   python examples/test_power_rails.py

Or use the CLI::

   colosseum run examples/test_power_rails.py --config examples/configs/bench.sim.toml

Test scripts should call ``col.endex()`` at the end of ``__main__`` so results flush and the process exits ``0`` or ``1``.

Extension authors: see :doc:`plugins` and the reference package at ``examples/plugins/myvendor_bench/``.
Bench PC checks: see :doc:`host_environment` and ``examples/test_host_profile.py``.

Minimal pattern::

   import colosseum as col

   def main():
       col.config.load_config("examples/configs/bench.sim.toml")
       col.equipment.dmm.measure_voltage(dmm_id=1, channel=1, key="vrail_3v3")
       col.equipment.dmm.verify_voltage(key="vrail_3v3", expected_val=3.3, tolerance=0.1)

   if __name__ == "__main__":
       main()
       col.endex()
