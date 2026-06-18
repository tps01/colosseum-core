Host environment (col.host)
===========================

The bundled ``colosseum_host`` plugin exposes ``col.host`` for measuring and verifying
bench PC prerequisites before hardware suites run. Call these APIs explicitly from test
scripts; the runner does not auto-run host checks.

Submodules
----------

``col.host.system``
   Cross-platform host facts: Python version, platform, memory, disk, uptime.

``col.host.bench``
   Lab-runtime prerequisites: VISA backend and serial port enumeration.

``col.host.config``
   Bench configuration snapshots: ``capture_host_profile`` writes ``host_profile.json``
   and registers a ``host_profile`` artifact.

Optional bench thresholds
-------------------------

Declare optional global thresholds under ``[host.profile]`` (use ``profile_id = 1``):

.. code-block:: toml

   [host.profile]
   profile_id = 1
   min_disk_gb = 5.0
   min_memory_mb = 2048
   python_version_prefix = "3.11"
   platform = "Windows"
   disk_path = "C:\\"

Your test script must call the matching verifiers; the section does not auto-enforce.

Platform notes
--------------

+---------------------------+-------------------------+-------------------------+
| Measurement               | Linux                   | Windows                 |
+===========================+=========================+=========================+
| Memory available          | ``/proc/meminfo``       | ``GlobalMemoryStatusEx``|
| Uptime                    | ``/proc/uptime``        | ``GetTickCount64``      |
| Disk free                 | ``shutil.disk_usage``   | ``shutil.disk_usage``   |
| Serial ports              | ``/dev/tty*`` via       | ``COM*`` via pyserial   |
|                           | pyserial                |                         |
| VISA backend              | pyvisa ResourceManager  | pyvisa ResourceManager  |
+---------------------------+-------------------------+-------------------------+

Serial enumeration requires read access to device nodes (Linux) or COM port metadata
(Windows). VISA requires a working backend (NI-VISA, pyvisa-py, or PyVISA-sim for
offline benches).

Example
-------

.. code-block:: python

   import colosseum as col

   col.config.load_config("examples/configs/bench.sim.toml")
   col.host.system.measure_memory_available_mb(key="mem_mb")
   col.host.system.verify_memory_available_mb(key="mem_mb", minimum=512.0)
   col.host.config.capture_host_profile(path="host_profile.json")
   col.endex()

See ``examples/test_host_profile.py`` and :doc:`platform_notes` for OS-specific setup.

See also
--------

* :doc:`plugins` — building third-party extensions
* :doc:`output_artifacts` — run directory layout
