First-party plugins
===================

Core is the runner and evidence model. Bench APIs live in separate distributions
you install into the **same** virtual environment as ``colosseum-core`` (GitHub
Release wheels; see :doc:`installation`). Core discovers them through
``colosseum.plugins`` entry points.

Each plugin publishes an API reference site. This page is the hub overview;
each site's **Getting started** guide shows config → procedure → verification
with ``driver = "sim"`` where possible.

.. list-table::
   :header-rows: 1
   :widths: 22 28 50

   * - Package
     - Namespace
     - Typical config
   * - `colosseum-equipment <https://tps01.github.io/colosseum-equipment/>`__
     - ``col.equipment.*``, ``col.io.*``
     - ``[[equipment.psu]]``, ``[equipment.dmm]``, ``[io.dio]``, …
   * - `colosseum-shared <https://tps01.github.io/colosseum-shared/>`__
     - ``col.shared.*``
     - none (pairs with other plugins' TOML)
   * - `colosseum-host <https://tps01.github.io/colosseum-host/>`__
     - ``col.host.*``
     - ``[host.profile]``
   * - `colosseum-messaging <https://tps01.github.io/colosseum-messaging/>`__
     - ``col.messaging.*``
     - ``[messaging.http]``, ``[messaging.ssh]``, …
   * - `colosseum-gui <https://tps01.github.io/colosseum-gui/>`__
     - ``col.gui.web``, ``col.gui.desktop``
     - ``[gui.web]``, ``[gui.desktop]``

Install example (same venv as core)::

   pip install colosseum_equipment-<version>-py3-none-any.whl
   pip install colosseum_shared-<version>-py3-none-any.whl

Getting started (per plugin)
----------------------------

* Equipment —
  `Getting started <https://tps01.github.io/colosseum-equipment/guides/getting_started.html>`__
* Shared —
  `Getting started <https://tps01.github.io/colosseum-shared/guides/getting_started.html>`__
* Host —
  `Getting started <https://tps01.github.io/colosseum-host/guides/getting_started.html>`__
* Messaging —
  `Getting started <https://tps01.github.io/colosseum-messaging/guides/getting_started.html>`__
* GUI —
  `Getting started <https://tps01.github.io/colosseum-gui/guides/getting_started.html>`__

(Links resolve after each plugin's Pages build includes the new guide.)

Copy-out procedures
-------------------

For full test stubs (rail voltage, GPIO, RF blocks, suites), copy folders from
the :doc:`testware_library` catalog rather than starting from an empty script.
