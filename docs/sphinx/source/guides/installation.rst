Installation
============

Colosseum ships as a single ``colosseum`` package. A normal install includes the
core runtime, simulated bench paths, config loading, evidence database, decorators,
CLI runner, and first-party API modules. Hardware transports, SSH, GUI, plotting,
and FT232H GPIO are optional extras. PyVISA-sim is for repository tests only
(``.[test]`` extra; install via ``pip install -e ".[test]"``).

End users (when published to PyPI)::

   pip install colosseum

Install optional capabilities only where needed::

   pip install "colosseum[hardware]"  # PyVISA + pyserial
   pip install "colosseum[ssh]"       # Paramiko SSH
   pip install "colosseum[gui]"       # desktop GUI runner
   pip install "colosseum[plot]"      # spectrum trace PNGs
   pip install "colosseum[io]"        # FT232H GPIO via pyftdi

From a source checkout::

   pip install -e .

Development tools (pytest, Sphinx, Cosmic Ray) are not included by default. Install
them with ``requirements-dev.txt``::

   pip install -r requirements-dev.txt

Or in one step from a checkout::

   pip install -e . && pip install -r requirements-dev.txt

System prerequisites
--------------------

Some optional capabilities need OS packages that pip cannot install:

- **Linux GUI:** ``python3-tk`` (stdlib ``tkinter`` for ``colosseum --gui`` with ``[gui]``)
- **Linux serial:** ``dialout`` group membership or udev rules for ``/dev/ttyUSB*`` with ``[hardware]``
- **VISA hardware:** a VISA implementation PyVISA can load (NI-VISA, Keysight IO Libraries,
  Tektronix VISA, Rohde & Schwarz, etc., or pure-Python ``pyvisa-py``). Not required for
  ``driver = "sim"``. Install ``colosseum[hardware]`` for PyVISA/serial. PyVISA-sim is optional for developers (``.[test]`` extra). Use
  ``python -m pyvisa info`` to see the active VISA backend.

Example (Debian/Ubuntu)::

   sudo apt-get install python3-tk

Offline / air-gapped install
----------------------------

See :doc:`offline_install` for building and installing from a pre-downloaded wheel
bundle without network access. Tarballs are for **bench end users** (runtime only).
Tests, docgen, and PyVISA-sim require a git clone and ``requirements-dev.txt``.

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

Compatibility extras
--------------------

Prior releases treated runtime dependencies as broadly installed. ``colosseum[bench]``
remains as a broad compatibility extra for hardware, SSH, GUI, and plotting. Prefer
the focused extras above for new environments. ``colosseum[equipment]`` maps to
hardware + plotting, ``colosseum[shared]`` maps to SSH, and ``[equipment-sim]`` keeps
the PyVISA-sim test dependency alias.

Dev-only extras: ``test``, ``docs``, ``mutation`` (or use ``requirements-dev.txt``).
