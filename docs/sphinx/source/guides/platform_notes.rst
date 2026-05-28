Platform notes
==============

**Windows**

- Output directories are under the process current working directory: ``outputs/``.
- VISA resources use industry-standard resource strings (``USB0::...``, ``COM1``, etc.).
- Serial ports use ``COM`` names from bench config.
- Create a virtual environment from the repository root::

     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     python -m pip install -U pip setuptools wheel
     python -m pip install -e ".[bench,test]"

  Or use ``scripts\start_environment.ps1`` (PowerShell) or ``scripts\start_environment.bat`` (``cmd.exe`` when script execution is disabled).
- **VISA / NI:** Install the vendor VISA runtime (e.g. NI-VISA) so ``pyvisa`` can list resources. Use ``python -m pyvisa info`` inside the venv to see the active backend.
- **Serial:** Confirm the COM port in Device Manager matches ``port`` / ``resource`` in bench TOML.

**Linux**

- Same layout and CLI; serial devices are typically ``/dev/ttyUSB*`` or ``/dev/ttyACM*``.
- Add your user to the ``dialout`` group (or udev rules) for serial access without root.
- VISA: install linux-gpib or vendor USB drivers as required; verify with ``python -m pyvisa info``.
- Use ``. ./scripts/start_environment.sh`` from the repository root to create and activate the development virtual environment.

**Offline / CI**

- Set ``driver = "sim"`` in bench config or use ``examples/configs/bench.sim.toml``.
- Set ``COLOSSEUM_BENCH_CONFIG=bench.sim.toml`` when running examples.
- For SCPI-level tests without hardware, use PyVISA-sim (Python 3.10+): ``pip install -e ".[equipment-sim]"`` and ``pytest -m visa_sim``. See ``docs/testing/pyvisa-sim-fixtures.md`` in the repository.

**Hardware regression**

- Copy ``configs/bench.local.toml.example`` to a gitignored ``configs/bench.local.toml`` and follow ``docs/testing/regression-test-procedure.md``.

**Troubleshooting**

- ``pyvisa`` / VISA connection errors: check ``resource`` strings with ``pyvisa-shell`` or the vendor utility; confirm the ``equipment`` or ``bench`` extra is installed.
- Empty or ``ERROR`` responses with ``visa_backend = "sim"``: verify ``sim_definition`` path and that YAML ``resources:`` keys match the bench ``resource``; see ``docs/testing/pyvisa-sim-fixtures.md``.
- Permission denied on serial (Linux): group membership or udev rules for the adapter.
