Platform notes
==============

Core uses platform-neutral Python APIs. Output is written beneath ``outputs/`` in the
process working directory unless ``--no-artifacts`` is used.

Windows
-------

Create and activate a virtual environment with::

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

Core itself needs no GUI toolkit. The optional desktop runner is
``colosseum-extensions`` (Qt / PySide6); see that package's docs for host prerequisites
(`GitHub <https://github.com/tps01/colosseum-extensions>`__).

Linux
-----

Create and activate a virtual environment with::

   python3 -m venv .venv
   . .venv/bin/activate

Core CLI and offline wheelhouses are headless. For the desktop runner, install
``colosseum-extensions`` and follow its platform notes for Qt libraries and display
requirements.

Documentation
-------------

The Sphinx **PDF** is the primary manual and needs ``latexmk`` plus a TeX
distribution. HTML is a backup of the same sources
(``python scripts/docgen/build_all.py --skip-pdf``).

Hardware permissions, native libraries, and driver runtimes are plugin concerns and
should be documented by the plugin that needs them.
