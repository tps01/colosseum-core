Installation
============

Install wheels from a **GitHub Release**, or from an offline wheelhouse built
for your OS and Python. The recipes below do not require a package index.

Python **3.9** and newer are supported for core. ``colosseum-equipment`` requires
**3.10** or newer when you install that plugin.

From a GitHub Release
---------------------

1. Install Python and create a virtual environment::

      python -m venv .venv

   Activate it (Windows)::

      .venv\Scripts\activate

   Activate it (Linux / macOS)::

      source .venv/bin/activate

2. Open the latest release for
   `colosseum-core <https://github.com/tps01/colosseum-core/releases>`__
   and download the wheel::

      colosseum_core-<version>-py3-none-any.whl

   Download compatible plugin wheels when you need them
   (for example ``colosseum_equipment-…whl``, ``colosseum_shared-…whl``). Each
   plugin has its own repository under
   `tps01 <https://github.com/tps01>`__.

3. Install into the active venv (paths relative to your download folder)::

      pip install colosseum_core-<version>-py3-none-any.whl
      pip install colosseum_equipment-<version>-py3-none-any.whl   # example plugin
      pip install colosseum_shared-<version>-py3-none-any.whl

   Install every plugin you need in the **same** environment as core. Core
   discovers plugins through ``colosseum.plugins`` entry points. Plugins are
   independently versioned: their version numbers need not match core. Check
   each plugin wheel's ``colosseum-core`` dependency range before installing.

4. Confirm the CLI::

      colosseum --help

   The Python import is ``import colosseum as col``. The desktop runner
   (``colosseum --gui``) ships with core; see :doc:`platform_notes` for Tcl/Tk
   notes on Linux.

5. Run a smoke test (replace paths with your script and config)::

      colosseum run my_test.py -g config.toml

See :doc:`quickstart` for a first script, and :doc:`testware_library` for
copy-out procedure stubs.

Offline wheelhouse from a release
---------------------------------

Release assets also include prebuilt offline archives. Prefer the file that
matches the target OS and Python minor::

   colosseum-core-offline-windows-py{3.9,3.12,3.14}.zip
   colosseum-core-offline-linux-py{3.9,3.12,3.14}.tar.gz

Each archive keeps wheels under ``wheels/`` and ships operator scripts at the
root:

* Windows: run ``install.bat``, then ``start_cli.bat`` (CLI) or ``start_gui.bat``
  (desktop runner).
* Linux: ``chmod +x install.sh start_*.sh && ./install.sh``, then
  ``./start_cli.sh`` or ``./start_gui.sh``.

Manual equivalent (after extract)::

   python -m pip install --no-index --find-links=wheels colosseum-core

Building a custom combined wheelhouse from a parent checkout is documented in
that checkout's ``offline/README.md``::

   python offline/build_wheelhouse.py
   python offline/install_offline.py --wheelhouse colosseum-wheelhouse
   python offline/verify_env.py

``customtkinter`` ships in the wheelhouse; system Tcl/Tk does not. On Linux, bake
``python3-tk`` (or a Tk-enabled Python) into the offline host image.

Editable install (developers)
-----------------------------

Clone the repository and install in editable mode when you are changing core
itself. One install covers runtime, tests, static analysis, and docs tooling::

   git clone https://github.com/tps01/colosseum-core.git
   cd colosseum-core
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # Linux / macOS
   pip install -U pip setuptools wheel
   pip install -e .

Install sibling plugin checkouts the same way (``pip install -e .`` in each
plugin repo) into that venv when you need their APIs.

Walkthrough plugins
-------------------

Manual examples that use ``col.template.*`` assume the ``colosseum-template``
example plugin (under ``examples/plugins/colosseum_template`` in the core
checkout), or a wheel built from that package. First-party bench plugins
(equipment, shared, host, …) are separate distributions; see
:doc:`first_party_plugins`.
