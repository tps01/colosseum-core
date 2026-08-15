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

Development tools (pytest, Sphinx, static analysis) are not included by default.
See ``docs/DEVELOPING.md`` for editable install, ``requirements-dev.txt``, and
``scripts/start_environment.*`` helpers.
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

Repository bootstrap scripts (``scripts/start_environment.ps1``, ``.bat``, and ``.sh``)
create ``.venv``, install the editable project, and optionally install
``requirements-dev.txt``. Full steps: ``docs/DEVELOPING.md``.

Compatibility extras
--------------------

Prior releases treated runtime dependencies as broadly installed. ``colosseum[bench]``
remains as a broad compatibility extra for hardware, SSH, GUI, and plotting. Prefer
the focused extras above for new environments. ``colosseum[equipment]`` maps to
hardware + plotting, ``colosseum[shared]`` maps to SSH, and ``[equipment-sim]`` keeps
the PyVISA-sim test dependency alias.

Dev-only extras: ``test``, ``docs`` (or use ``requirements-dev.txt``; see ``docs/DEVELOPING.md``).
