Running suites
==============

Suites are defined in TOML beside your tests::

   name = "smoke"
   setup = ["setup/prepare_bench.py"]
   tests = ["tests/test_power_rails.py"]
   teardown = ["teardown/power_down.py"]

Run::

   colosseum run-suite suites/smoke.toml --config examples/configs/bench.sim.toml
   colosseum run-suite suites/smoke.toml --autoconfig --autoconfig-blacklist "Ethernet 1,192.168.1.10"

Paths are relative to the suite file directory. Setup, all tests, and teardown share one output directory and one ``execution.sqlite``. Setup failure skips tests but still runs teardown; the process exits ``1``.
