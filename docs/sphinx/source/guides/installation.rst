Installation
============

Colosseum is split into separately installable distributions:

- ``colosseum-core`` — runtime, CLI, config, evidence database, decorators
- ``colosseum-shared`` — ``col.shared.*`` (SSH, regex, parsing)
- ``colosseum-host`` — ``col.host.*`` (bench PC checks)
- ``colosseum-equipment`` — ``col.equipment.*`` and ``col.io.*``

The Python import remains ``import colosseum as col``. Plugins register through
``colosseum.plugins`` entry points after install.

End users (when published to PyPI)::

   pip install colosseum-core
   pip install "colosseum-shared[ssh]"
   pip install colosseum-host
   pip install "colosseum-equipment[hardware]"

Or install the core ``[bench]`` extra once plugins are published::

   pip install "colosseum-core[bench]"

Optional capabilities::

   pip install "colosseum-equipment[hardware]"  # PyVISA + pyserial
   pip install "colosseum-shared[ssh]"          # Paramiko SSH
   pip install "colosseum-core[gui]"            # desktop GUI runner
   pip install "colosseum-equipment[plot]"      # spectrum trace PNGs
   pip install "colosseum-equipment[io]"        # FT232H GPIO via pyftdi

From sibling source checkouts::

   pip install -e ./colosseum-core
   pip install -e ./colosseum-shared[ssh]
   pip install -e ./colosseum-host
   pip install -e ./colosseum-equipment[hardware,test]

Development tools (pytest, Sphinx, static analysis) are not included by default.
See ``docs/DEVELOPING.md`` for editable install, ``requirements-dev.txt``, and
``scripts/start_environment.*`` helpers.
System prerequisites
--------------------

Some optional capabilities need OS packages that pip cannot install:

- **Linux GUI:** ``python3-tk`` (stdlib ``tkinter`` for ``colosseum --gui`` with ``colosseum-core[gui]``)
- **Linux serial:** ``dialout`` group membership or udev rules for ``/dev/ttyUSB*`` with equipment hardware extras
- **VISA hardware:** a VISA implementation PyVISA can load (NI-VISA, Keysight IO Libraries,
  Tektronix VISA, Rohde & Schwarz, etc., or pure-Python ``pyvisa-py``). Not required for
  ``driver = "sim"``. Install ``colosseum-equipment[hardware]`` for PyVISA/serial. PyVISA-sim is
  optional for developers (``colosseum-equipment[test]``). Use ``python -m pyvisa info`` to see
  the active VISA backend.

Example (Debian/Ubuntu)::

   sudo apt-get install python3-tk

Offline / air-gapped install
----------------------------

See :doc:`offline_install` for building and installing from a pre-downloaded wheel
bundle without network access. Tarballs are for **bench end users** (runtime only).
Tests, docgen, and PyVISA-sim require git clones and ``requirements-dev.txt``.

Source checkout helpers
-----------------------

Repository bootstrap scripts (``scripts/start_environment.ps1``, ``.bat``, and ``.sh``)
create ``.venv``, install the editable core package plus sibling plugins from
``requirements-dev.txt``. Full steps: ``docs/DEVELOPING.md``.
