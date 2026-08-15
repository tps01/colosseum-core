Platform notes
==============

Core uses platform-neutral Python APIs. Output is written beneath ``outputs/`` in the
process working directory unless ``--no-artifacts`` is used.

Windows
-------

Create and activate a virtual environment with::

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

The optional GUI uses the standard ``tkinter`` runtime included with normal CPython
installers.

Linux
-----

Create and activate a virtual environment with::

   python3 -m venv .venv
   . .venv/bin/activate

The GUI may require ``python3-tk`` and a display server.

Documentation
-------------

HTML documentation requires only the ``docs`` extra. PDF generation additionally needs
``latexmk`` and a TeX distribution. Use ``python scripts/docgen/build_all.py --skip-pdf``
for an HTML-only build.

Hardware permissions, native libraries, and driver runtimes are plugin concerns and
should be documented by the plugin that needs them.
