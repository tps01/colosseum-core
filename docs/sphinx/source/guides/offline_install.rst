Offline install
===============

Use a pre-built wheel bundle when the **bench or embedded target** has no PyPI or internet access.
Bundles ship **runtime dependencies only** (the same wheels as ``pip install colosseum``).
They do **not** include pytest, Sphinx, docgen, PyVISA-sim, or other developer tooling.

Developers
----------

Clone the repository and install dev dependencies on a connected machine::

   pip install -e .
   pip install -r requirements-dev.txt

Use that environment for ``pytest``, ``python scripts/docgen/build_all.py``, and
``python scripts/run_tests.py``. See ``docs/testing/README.md``.

Building a bundle (connected machine, for end users)
----------------------------------------------------

From a source checkout with network access, use the **same Python minor** you will run on the air-gapped bench (Colosseum supports Python 3.9+; **3.11 is recommended** for new Windows/Linux benches)::

   py -3.11 scripts/package_offline.py
   # or: py -3.9 scripts/package_offline.py

This produces:

- ``wheelhouse/`` — downloaded runtime wheels (gitignored)
- ``offline-bundle/`` — staged install tree (gitignored)
- ``colosseum-<ver>-offline-<platform>-py<XY>.tar.gz`` — tarball to copy to the air-gapped host

For embedded targets (e.g. aarch64), build the bundle on a machine matching the target
Python version and architecture, or build wheels on-target from the sdist.

Installing on a disconnected host
---------------------------------

Copy the tarball to the target, then::

   tar xzf colosseum-0.3.0-offline-linux-x86_64-py311.tar.gz
   cd offline-bundle
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --no-index --find-links=wheels colosseum==0.3.0
   colosseum run smoke/run_sim.py --config smoke/bench.sim.toml

Replace the version and archive name with your bundle. The ``pyXY`` segment in the archive name (for example ``py311``) must match the Python used on the target host.

Windows 11 (air-gapped)
-----------------------

On a connected Windows machine, build the bundle with the target interpreter (for example ``py -3.11``). Copy ``colosseum-*-offline-windows-amd64-py311.tar.gz`` to the bench PC, then in PowerShell::

   tar -xzf colosseum-0.3.0-offline-windows-amd64-py311.tar.gz
   cd offline-bundle
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install --no-index --find-links=wheels colosseum==0.3.0
   colosseum run smoke\run_sim.py --config smoke\bench.sim.toml

Install **NI-VISA** (or your vendor VISA runtime) before using ``driver = "visa"`` instruments. Verify with ``python -m pyvisa info`` inside the venv. For Python 3.9 benches, build and install a ``py39`` bundle the same way.

Docker validation (optional)
----------------------------

On a connected Linux host with Docker, verify the bundle installs without network::

   python scripts/package_offline.py
   docker run --rm --network none -v "$PWD/offline-bundle:/bundle:ro" python:3.11-slim \
     bash -c 'python -m venv /tmp/v && /tmp/v/bin/pip install --no-index --find-links=/bundle/wheels colosseum && /tmp/v/bin/colosseum --help'

Regression check (repository developers / CI)
---------------------------------------------

From a git clone on a connected machine (validates bundle contents, not for air-gapped hosts)::

   python tests/regression/run_offline_install_check.py

This builds a runtime-only bundle, installs into a temporary virtual environment with
``--no-index``, and runs the sim smoke test.

Yocto / embedded Linux
----------------------

For Poky/QEMU validation on minimal embedded images, see ``infra/yocto/README.md`` and
``docs/testing/regression-test-procedure.md`` (R-OFFLINE-01). That procedure is manual
and is not part of GitHub Actions CI.
