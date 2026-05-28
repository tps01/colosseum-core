Installation
============

Colosseum ships as the ``colosseum`` package with optional bench extras.

Core only (config, decorators, runner, SQLite evidence)::

   pip install colosseum

Bench stack (equipment, shared, VISA/serial/SSH dependencies)::

   pip install "colosseum[bench]"

Documentation build tools::

   pip install "colosseum[docs]"

From a source checkout, install in editable mode with ``PYTHONPATH`` or ``pip install -e ".[bench,docs]"``.

Source checkout helpers
-----------------------

The repository includes setup scripts for common shells. They create ``.venv``, install the editable project with the default development extras, and activate the environment.

Windows PowerShell::

   .\scripts\start_environment.ps1

Windows ``cmd.exe`` when PowerShell script execution is disabled::

   scripts\start_environment.bat

Linux/macOS shell::

   . ./scripts/start_environment.sh

The shell script should be sourced with ``.`` if activation should remain in the current shell.

Set ``EXTRAS`` to override the default editable install extras::

   EXTRAS=bench,test,docs,mutation . ./scripts/start_environment.sh
