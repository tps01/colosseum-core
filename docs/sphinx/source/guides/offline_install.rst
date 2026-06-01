Offline install
===============

Use a pre-built wheel bundle when the target machine has no PyPI or internet access.

Building a bundle (connected machine)
-------------------------------------

From a source checkout with network access::

   python scripts/package_offline.py

This produces:

- ``wheelhouse/`` — downloaded wheels (gitignored)
- ``offline-bundle/`` — staged install tree (gitignored)
- ``colosseum-<ver>-offline-<platform>-py<XY>.tar.gz`` — tarball to copy to the air-gapped host

Include dev tools (pytest, Sphinx, Cosmic Ray) in the bundle::

   python scripts/package_offline.py --include-dev

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

Replace the version and archive name with your bundle.

Docker validation (optional)
----------------------------

On a connected Linux host with Docker, verify the bundle installs without network::

   python scripts/package_offline.py
   docker run --rm --network none -v "$PWD/offline-bundle:/bundle:ro" python:3.11-slim \
     bash -c 'python -m venv /tmp/v && /tmp/v/bin/pip install --no-index --find-links=/bundle/wheels colosseum && /tmp/v/bin/colosseum --help'

Regression check
----------------

From the repository root (connected machine)::

   python tests/regression/run_offline_install_check.py

This builds a bundle, installs into a temporary virtual environment with
``--no-index``, and runs the sim smoke test.

Yocto / embedded Linux
----------------------

For Poky/QEMU validation on minimal embedded images, see ``infra/yocto/README.md`` and
``docs/testing/regression-test-procedure.md`` (R-OFFLINE-01). That procedure is manual
and is not part of GitHub Actions CI.
