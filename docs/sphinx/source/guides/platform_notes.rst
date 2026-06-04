Platform notes
==============

**Windows**

- Output directories are under the process current working directory: ``outputs/``.
- VISA resources use industry-standard resource strings (``USB0::...``, ``GPIB0::18::INSTR``, ``ASRL15::INSTR``, ``COM1``, etc.). Omit ``driver`` in bench TOML for lab gear; it defaults to VISA/SCPI.
- Serial ports use ``COM`` names from bench config (or ASRL resources via VISA).
- Create a virtual environment from the repository root::

     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     python -m pip install -U pip setuptools wheel
     python -m pip install -e .
     python -m pip install -r requirements-dev.txt

  Or use ``scripts\start_environment.ps1`` (PowerShell) or ``scripts\start_environment.bat`` (``cmd.exe`` when script execution is disabled).
- **VISA:** Install any IVI-compatible runtime PyVISA can use (NI-VISA, Keysight IO Libraries,
  Tektronix VISA, etc.) or use ``pyvisa-py`` if you have no vendor stack. Colosseum calls
  ``pyvisa.ResourceManager()`` and does not hard-code NI. Use ``python -m pyvisa info`` inside
  the venv to see which backend is active when multiple VISA installs coexist.
- **Multiple VISA stacks:** set optional ``visa_library`` on an ``equipment.*`` entry (PyVISA
  ``ResourceManager`` argument, for example ``@ivi`` or ``@py``) or use environment variables
  documented by your vendor. See the generated :doc:`bench_config_reference`.
- **Serial:** Confirm the COM port in Device Manager matches ``port`` / ``resource`` in bench TOML.
- **Documentation PDF:** ``python scripts/docgen/build_all.py`` builds HTML and PDF; install MiKTeX or TeX Live with ``latexmk`` on ``PATH``, or use ``--skip-pdf`` for HTML only.

**Linux**

- Same layout and CLI; serial devices are typically ``/dev/ttyUSB*`` or ``/dev/ttyACM*``.
- Add your user to the ``dialout`` group (or udev rules) for serial access without root.
- VISA: install linux-gpib or vendor USB drivers as required; verify with ``python -m pyvisa info``.
- Use ``. ./scripts/start_environment.sh`` from the repository root to create and activate the development virtual environment.
- **Documentation PDF:** same as Windows; on Debian/Ubuntu install ``latexmk`` and ``texlive-latex-recommended`` (see CI in ``.github/workflows/ci.yml``).

**Offline / air-gapped install (Windows or Linux)**

- Build the offline bundle with the Python minor you will use on the bench: ``py -3.11 scripts/package_offline.py`` (or ``py -3.9``). See :doc:`offline_install`.
- **Windows:** right-click the ``.tar.gz`` → **Extract All**, open ``offline-bundle``, run ``install.ps1`` or ``install.bat``.
- **Linux:** ``tar xzf colosseum-*-offline-*.tar.gz``, ``cd offline-bundle``, run ``./install.sh``.
- Run the bundled smoke test: ``colosseum run smoke/run_sim.py --config smoke/bench.sim.toml``.

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

**VISA sessions and cleanup**

- End every test script with ``col.endex()`` so results, logs, and instrument sessions are released. ``colosseum run`` calls ``endex()`` in a ``finally`` block even when the script fails.
- Colosseum closes cached instruments before their transports on shutdown. Spectrum analyzers may send a final ``DISP:UPD ON`` while the session is still open.
- If a script exits without ``endex()``, the equipment plugin registers a best-effort ``atexit`` handler that calls ``close_all()`` when a runtime context exists and is not yet finalized. That handler does **not** write summaries or exit codes; prefer ``endex()`` or ``colosseum run``.
- ``atexit`` does not run on ``kill -9`` or hard crashes. After an abnormal exit, confirm no other process holds the instrument (another Python REPL, vendor UI, LabVIEW), then retry. On Windows, end stray ``python.exe`` tasks if ``resource locked`` persists; power-cycle or reset VISA only as a last resort.

**Troubleshooting**

- ``pyvisa`` / VISA connection errors: check ``resource`` strings with ``pyvisa-shell`` or the vendor utility; confirm ``colosseum`` is installed with its dependencies intact. Colosseum maps PyVISA failures to ``EquipmentConnectionError`` (including invalid/closed sessions and locked resources) or ``EquipmentTimeoutError`` (VISA timeout).
- **Resource locked / in use:** another session holds the same ``resource`` string; close other apps or zombie Python processes before re-running.
- Empty or ``ERROR`` responses with ``visa_backend = "sim"``: verify ``sim_definition`` path and that YAML ``resources:`` keys match the bench ``resource``; see ``docs/testing/pyvisa-sim-fixtures.md``.
- Permission denied on serial (Linux): group membership or udev rules for the adapter.
- **FT232H GPIO (``col.io.dio``):** install ``pip install colosseum[io]`` for pyftdi. On Windows, assign WinUSB to the FT232H with Zadig (USB serial alone is not enough for MPSSE GPIO). On Linux, install ``libusb`` and ensure udev permissions for the adapter. See :doc:`io_digital`.

**GUI runner**

- Requires ``python3-tk`` on Linux (see :doc:`installation`).
- Launch from the bench or repository working directory: ``colosseum --gui``.
- Pick a test script (``.py``) or suite (``.toml``), optional bench config TOML, and use **Run test** / **Run suite**. Live log output tails ``debug.log``; completed runs appear in the run list with summary and verification details.
- Default config path: set ``COLOSSEUM_BENCH_CONFIG`` or choose a file in the GUI.
- **SSH / X11 forwarding:** connect with ``ssh -X user@host`` (or ``-Y`` if needed), ensure ``DISPLAY`` is set on the remote session, and run ``colosseum --gui`` on the bench machine. The GUI window is forwarded to your local X server (VcXsrv, X410, WSLg, etc.); instrument access stays on the remote host. For the Yocto QEMU lab, see ``docs/testing/qemu-yocto-regression.md``.
- **Windows:** run ``colosseum --gui`` locally; no ``DISPLAY`` variable is required.
