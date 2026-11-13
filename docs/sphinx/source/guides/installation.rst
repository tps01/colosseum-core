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

   The Python import is ``import colosseum as col``. The optional desktop
   runner lives in the separate ``colosseum-extensions`` package
   (`GitHub <https://github.com/tps01/colosseum-extensions>`__); install it, then run
   ``colosseum --gui``. See :doc:`platform_notes` and the
   `UI docs <https://tps01.github.io/colosseum-extensions/>`__.

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

Each archive keeps wheels under ``wheels/`` and ships CLI operator scripts at the
root (core bundles are headless):

* Windows: run ``install.bat``, then ``start_cli.bat``.
* Linux: ``chmod +x install.sh start_*.sh && ./install.sh``, then
  ``./start_cli.sh``.

Manual equivalent (after extract)::

   python -m pip install --no-index --find-links=wheels colosseum-core

Desktop operators install the separate ``colosseum-extensions`` offline bundle from that
package's GitHub Releases (see
`colosseum-extensions <https://github.com/tps01/colosseum-extensions>`__).

Building a custom combined wheelhouse from a parent checkout is documented in
that checkout's ``offline/README.md``::

   python offline/build_wheelhouse.py
   python offline/install_offline.py --wheelhouse colosseum-wheelhouse
   python offline/verify_env.py

Editable install (developers)
-----------------------------

Clone the repository and install from ``requirements.txt`` when you are changing
core itself. That file editable-installs the package and adds test, static
analysis, and docs tooling. A release wheel installs runtime dependencies only::

   git clone https://github.com/tps01/colosseum-core.git
   cd colosseum-core
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # Linux / macOS
   pip install -U pip setuptools wheel
   pip install -r requirements.txt

Install sibling plugin checkouts into that venv when you need their APIs
(``pip install -e .`` for runtime only, or ``pip install -r requirements.txt``
in each plugin repo for development).

Walkthrough plugins
-------------------

Manual examples that use ``col.template.*`` assume the ``colosseum-template``
example plugin (under ``examples/plugins/colosseum_template`` in the core
checkout), or a wheel built from that package. First-party bench plugins
(equipment, shared, host, …) are separate distributions; see
:doc:`first_party_plugins`.

Optional standalone executable
------------------------------

The intended way to run Colosseum remains ``colosseum run`` and
``colosseum run-suite`` from a virtual environment. If you need a frozen
onedir launcher for operators who will not install Python, see
:doc:`freezing`. That path is optional and is not required for normal use.
