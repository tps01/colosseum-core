Installation
============

Colosseum ships as a single ``colosseum`` package. A normal install includes the full
runtime stack: VISA/serial equipment transports, SSH (``col.shared``), PyVISA-sim,
and the optional GUI runner (``customtkinter``).

End users (when published to PyPI)::

   pip install colosseum

From a source checkout::

   pip install -e .

Development tools (pytest, Sphinx, Cosmic Ray) are not included by default. Install
them with ``requirements-dev.txt``::

   pip install -r requirements-dev.txt

Or in one step from a checkout::

   pip install -e . && pip install -r requirements-dev.txt

System prerequisites
--------------------

Some capabilities need OS packages that pip cannot install:

- **Linux GUI:** ``python3-tk`` (stdlib ``tkinter`` for ``colosseum --gui``)
- **Linux serial:** ``dialout`` group membership or udev rules for ``/dev/ttyUSB*``
- **VISA hardware:** a VISA implementation PyVISA can load (NI-VISA, Keysight IO Libraries,
  Tektronix VISA, Rohde & Schwarz, etc., or pure-Python ``pyvisa-py``). Not required for
  ``driver = "sim"`` or PyVISA-sim. Use ``python -m pyvisa info`` to see the active backend.

Example (Debian/Ubuntu)::

   sudo apt-get install python3-tk

Offline / air-gapped install
----------------------------

See :doc:`offline_install` for building and installing from a pre-downloaded wheel
bundle without network access.

Source checkout helpers
-----------------------

The repository includes setup scripts for common shells. They create ``.venv``,
install the editable project with dev dependencies, and activate the environment.

Windows PowerShell::

   .\scripts\start_environment.ps1

Windows ``cmd.exe`` when PowerShell script execution is disabled::

   scripts\start_environment.bat

Linux/macOS shell::

   . ./scripts/start_environment.sh

The shell script should be sourced with ``.`` if activation should remain in the current shell.

Set ``SKIP_DEV=1`` to install runtime only (no ``requirements-dev.txt``)::

   SKIP_DEV=1 . ./scripts/start_environment.sh

Deprecated extras
-----------------

Prior releases used optional extras such as ``colosseum[bench]``, ``[gui]``, and
``[equipment-sim]``. Runtime dependencies are now installed by default. Those extras
remain as empty aliases for one release cycle and will be removed in 0.4.0.

Dev-only extras: ``test``, ``docs``, ``mutation`` (or use ``requirements-dev.txt``).
