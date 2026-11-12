First-party plugins
===================

Find an API by task
-------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Plugin and workflow
   * - Control bench instruments
     - `Equipment <https://tps01.github.io/colosseum-equipment/guides/instrument_workflows.html>`__
   * - Read serial data or send SCPI
     - `Equipment serial and SCPI <https://tps01.github.io/colosseum-equipment/guides/serial_ports.html>`__
   * - Check values, files, or logs
     - `Shared <https://tps01.github.io/colosseum-shared/guides/evidence_workflows.html>`__
   * - Send HTTP requests
     - `Messaging HTTP <https://tps01.github.io/colosseum-messaging/guides/http.html>`__
   * - Execute SSH commands or transfer remote files
     - `Messaging SSH <https://tps01.github.io/colosseum-messaging/guides/ssh.html>`__
       and `file transfer <https://tps01.github.io/colosseum-messaging/guides/transfers.html>`__
   * - Monitor local CPU, memory, processes, or network interfaces
     - `Host <https://tps01.github.io/colosseum-host/guides/telemetry_workflows.html>`__
   * - Automate a browser or desktop application
     - `GUI automation <https://tps01.github.io/colosseum-gui/guides/drivers_locators.html>`__
   * - Launch and monitor Colosseum tests
     - Core desktop runner: ``colosseum --gui``

Serial/SCPI talks to a configured instrument or serial port. SSH executes on a
remote operating system. Host inspects the machine running the Colosseum
process. Select the API according to that execution location and interface.

Core is the runner and evidence model. Bench APIs live in separate distributions
you install into the **same** virtual environment as ``colosseum-core`` (GitHub
Release wheels; see :doc:`installation`). Core discovers them through
``colosseum.plugins`` entry points.

Each plugin publishes workflows, configuration, and API reference. This page is the hub overview;
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
     - ``[equipment.psu]``, ``[equipment.dmm]``, ``[io.dio]``, …
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
  ·
  `Config reference <https://tps01.github.io/colosseum-equipment/config_reference.html>`__
  (instrument rows:
  `config_instruments <https://tps01.github.io/colosseum-equipment/config_instruments.html>`__,
  I/O rows:
  `config_io <https://tps01.github.io/colosseum-equipment/config_io.html>`__)
* Shared —
  `Getting started <https://tps01.github.io/colosseum-shared/guides/getting_started.html>`__
  ·
  `Config reference <https://tps01.github.io/colosseum-shared/config_reference.html>`__
* Host —
  `Getting started <https://tps01.github.io/colosseum-host/guides/getting_started.html>`__
  ·
  `Config reference <https://tps01.github.io/colosseum-host/config_reference.html>`__
* Messaging —
  `Getting started <https://tps01.github.io/colosseum-messaging/guides/getting_started.html>`__
  ·
  `Config reference <https://tps01.github.io/colosseum-messaging/config_reference.html>`__
* GUI —
  `Getting started <https://tps01.github.io/colosseum-gui/guides/getting_started.html>`__
  ·
  `Config reference <https://tps01.github.io/colosseum-gui/config_reference.html>`__

(Links resolve after each plugin's Pages build includes the guide and the
config reference.)

Example test procedures
-----------------------

For full test stubs (rail voltage, GPIO, RF blocks, suites), copy folders from
the :doc:`testware_library` catalog rather than starting from an empty script.
