Packaging a standalone executable
=================================

The intended way to run Colosseum is still ``colosseum run`` and
``colosseum run-suite`` from a Python virtual environment with core and the
plugins you need installed. See :doc:`installation` and :doc:`running_tests`.

This page describes an **optional** packaging path for people who want a
standalone onedir bundle (a launcher plus an ``_internal`` folder) that they
can ship without asking operators to create a venv. It is not required for
normal use of the framework.

What gets frozen
----------------

``python -m colosseum.tools.build_executable`` freezes the **active**
environment. Every distribution that exposes a ``colosseum.plugins`` entry
point in that environment is collected into the bundle, along with colosseum
core. Install only the plugins you want to ship before you build.

Test scripts, suite TOML files, and config files stay **outside** the archive.
Operators run the frozen launcher the same way they would the CLI::

   colosseum.exe run my_test.py -g config.toml
   colosseum.exe run-suite suite.toml -g config.toml

On Linux and macOS the launcher is named ``colosseum`` (no ``.exe``).

Build steps
-----------

1. Create and activate a virtual environment, then install core and the plugin
   wheels you need (see :doc:`installation`). A normal core install already
   pulls in PyInstaller.

2. From the project directory that holds your scripts and configs, run::

      python -m colosseum.tools.build_executable

Outputs
-------

PyInstaller writes an onedir layout under ``dist/colosseum/``:

* Windows: ``colosseum.exe`` next to ``_internal/``
* Linux / macOS: ``colosseum`` next to ``_internal/``

The same command then packs that folder into an archive next to it:

* Windows: ``dist/colosseum.zip``
* Linux / macOS: ``dist/colosseum.tar.gz``

Members use a ``colosseum/`` prefix, so extracting the archive recreates a
runnable directory.

Limits
------

* System instrument libraries such as NI-VISA are not copied into the bundle.
  Install them on the target machine when your config uses VISA instruments.
* Playwright browsers are a separate download; freezing ``colosseum-gui`` does
  not ship browser binaries.
* Adding or removing a plugin means rebuilding the executable.
