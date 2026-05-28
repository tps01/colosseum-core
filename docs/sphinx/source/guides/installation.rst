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
