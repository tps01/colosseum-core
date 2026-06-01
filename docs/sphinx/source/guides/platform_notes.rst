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
     python -m pip install -e .
     python -m pip install -r requirements-dev.txt

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
- For SCPI-level tests without hardware, use PyVISA-sim (Python 3.10+): ``pytest -m visa_sim``. See ``docs/testing/pyvisa-sim-fixtures.md`` in the repository.

**Hardware regression**

- Copy ``configs/bench.local.toml.example`` to a gitignored ``configs/bench.local.toml`` and follow ``docs/testing/regression-test-procedure.md``.

**QEMU / Yocto regression (Tier 4C)**

- Build ``colosseum-qemu-image`` and run manual regression per ``docs/testing/qemu-yocto-regression.md`` and ``infra/yocto/README.md``.
- Host SSH cases use ``infra/yocto/conf/bench.qemu.toml`` (port 2222).
- Offline install and GUI cases install Colosseum on the guest via offline wheel bundle.

**Troubleshooting**

- ``pyvisa`` / VISA connection errors: check ``resource`` strings with ``pyvisa-shell`` or the vendor utility; confirm ``colosseum`` is installed with its dependencies intact.
- Empty or ``ERROR`` responses with ``visa_backend = "sim"``: verify ``sim_definition`` path and that YAML ``resources:`` keys match the bench ``resource``; see ``docs/testing/pyvisa-sim-fixtures.md``.
- Permission denied on serial (Linux): group membership or udev rules for the adapter.

**GUI runner**

- Requires ``python3-tk`` on Linux (see :doc:`installation`).
- Launch from the bench or repository working directory: ``colosseum --gui``.
- Pick a test script (``.py``) or suite (``.toml``), optional bench config TOML, and use **Run test** / **Run suite**. Live log output tails ``debug.log``; completed runs appear in the run list with summary and verification details.
- Default config path: set ``COLOSSEUM_BENCH_CONFIG`` or choose a file in the GUI.
- **SSH / X11 forwarding:** connect with ``ssh -X user@host`` (or ``-Y`` if needed), ensure ``DISPLAY`` is set on the remote session, and run ``colosseum --gui`` on the bench machine. The GUI window is forwarded to your local X server (VcXsrv, X410, WSLg, etc.); instrument access stays on the remote host. For the Yocto QEMU lab, see ``docs/testing/qemu-yocto-regression.md``.
- **Windows:** run ``colosseum --gui`` locally; no ``DISPLAY`` variable is required.
