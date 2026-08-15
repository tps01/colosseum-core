Installation
============

Install the standalone runtime::

   pip install colosseum-core

The Python import is ``import colosseum as col``. Install each plugin distribution in the
same environment; core discovers plugins through ``colosseum.plugins`` entry points.

The optional desktop runner is available with::

   pip install "colosseum-core[gui]"

Development tools are intentionally separate::

   python -m pip install -r requirements-dev.txt

Python 3.9 and newer are supported. Linux GUI use may require the operating system's
``python3-tk`` package.
