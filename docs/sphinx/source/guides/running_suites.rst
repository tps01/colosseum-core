Running suites
==============

Suites are TOML files whose script paths are relative to the suite file::

   name = "smoke"
   setup = ["setup/prepare.py"]
   tests = ["tests/check_device.py"]
   teardown = ["teardown/cleanup.py"]

Run a suite with::

   colosseum run-suite suites/smoke.toml --config bench.toml

Setup, test, and teardown scripts share one runtime and output directory. A setup failure
skips tests but still runs teardown. Test failures do not prevent later tests or teardown
from running.
