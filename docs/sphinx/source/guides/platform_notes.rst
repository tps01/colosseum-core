Platform notes
==============

Core uses platform-neutral Python APIs. Output is written beneath ``outputs/`` in the
process working directory unless ``--no-artifacts`` is used.

Windows
-------

Create and activate a virtual environment with::

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

python.org CPython installers include ``tkinter``, so ``colosseum --gui`` works after a
normal ``colosseum-core`` (or offline wheelhouse) install.

Linux
-----

Create and activate a virtual environment with::

   python3 -m venv .venv
   . .venv/bin/activate

For GUI use, the Python build must provide ``tkinter`` (Debian/Ubuntu: ``python3-tk``).
That is an OS/image prerequisite, not a pip package. Air-gapped hosts should bake it into
the golden image together with Python. See ``offline/README.md`` in the integration
checkout.

SSH X11 forwarding (``ssh -X``) still requires Tk on the Linux side and a working
``DISPLAY``.

Documentation
-------------

HTML documentation requires only the ``docs`` extra. PDF generation additionally needs
``latexmk`` and a TeX distribution. Use ``python scripts/docgen/build_all.py --skip-pdf``
for an HTML-only build.

Hardware permissions, native libraries, and driver runtimes are plugin concerns and
should be documented by the plugin that needs them.
