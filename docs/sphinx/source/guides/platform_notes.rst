Platform notes
==============

**Windows**

- Output directories are under the process current working directory: ``outputs/``.
- VISA resources use industry-standard resource strings (``USB0::...``, ``COM1``, etc.).
- Serial ports use ``COM`` names from bench config.

**Linux**

- Same layout and CLI; serial devices are typically ``/dev/ttyUSB*``.
- Ensure bench user permissions for serial and VISA devices.

**Offline / CI**

- Set ``driver = "sim"`` in bench config or use ``examples/configs/bench.sim.toml``.
- Set ``COLOSSEUM_BENCH_CONFIG=bench.sim.toml`` when running examples.
