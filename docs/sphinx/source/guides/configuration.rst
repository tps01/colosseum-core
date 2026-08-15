Configuration
=============

Bench resources are described in TOML. A section may be a single table or an array of tables; Colosseum normalizes both forms.

String values may be written with or without quotes when they are plain words (letters, digits, ``_``, ``-``) or VISA/path tokens. Booleans and numbers stay unquoted. These are equivalent::

   model = keysight-e4407b
   model = "keysight-e4407b"

Example PSU entry (``driver`` omitted — defaults to VISA/SCPI)::

   [[equipment.psu]]
   psu_id = 1
   resource = USB0::0x1234::0x5678::INSTR
   voltage = 3.3

Example VSG and spectrum analyzer entries::

   [[equipment.vsg]]
   vsg_id = 1
   model = keysight-esg
   resource = GPIB0::19::INSTR
   frequency = 1e9
   power_dbm = -10.0

   [[equipment.speca]]
   speca_id = 1
   model = keysight-e4407b
   resource = GPIB0::18::INSTR
   center_freq = 1e9
   span = 10e6
   rbw = 100e3

For lab benches, ``driver`` defaults to ``visa`` (PyVISA + SCPI). Set ``driver = sim`` for offline smoke/CI, or ``driver = serial`` on ``equipment.serial`` raw port channels.

Plugins register repeatable sections at load time (for example ``equipment.psu``, ``equipment.vsg``, ``equipment.speca``, ``shared.ssh``). Unknown keys in a section log a warning; missing required keys fail when the resource is first used.

Required and optional keys per section (generated from code) are in :doc:`bench_config_reference`. Build the HTML manual with ``python scripts/docgen/build_all.py`` to refresh that page.

For repository developers and CI (git clone + ``.[test]`` extra, not offline tarballs):

* ``examples/configs/bench.sim.toml`` — ``driver = "sim"`` (PSU/DMM cooperative sim)
* ``examples/configs/bench.visa-sim.toml`` — PyVISA-sim for DMM/PSU SCPI (dev/CI; ``.[test]`` extra)
* ``examples/configs/bench.rf.visa-sim.toml`` — PyVISA-sim for VSG and speca (dev/CI; Python 3.10+)

See :doc:`rf_equipment` for RF workflow examples.

Automatic configuration
-----------------------

When a bench TOML file is not needed, call ``col.equipment.autoconfig()`` after ``import colosseum as col``. This scans VISA INSTR resources, queries ``*IDN?`` on each, maps responses to equipment kinds/models, and populates the same internal config store used by ``load_config()``. Requires ``pip install colosseum-equipment[hardware]``.

ID assignment when several devices share a kind uses connection order **TCPIP → USB → GPIB → ASRL → PXI**, then numeric address within each connection type. The generated configuration is written to ``debug.log`` (INFO lines per assignment).

Example::

   col.equipment.autoconfig()
   col.equipment.psu.set_voltage(psu_id=1, voltage=3.3)

On a multi-homed PC, pass ``blacklist`` with an interface name or local IPv4 address to skip TCPIP discovery on that network (GPIB/USB/ASRL are still scanned)::

   col.equipment.autoconfig(blacklist="Ethernet 1")
   col.equipment.autoconfig(blacklist="192.168.1.10")
   col.equipment.autoconfig(blacklist=["eth0", "192.168.50.2"])

Unrecognized instruments are skipped with a log warning; autoconfig fails if no classifiable resources remain.

Export a generated TOML file for review or later ``load_config`` use::

   col.equipment.autoconfig(export_path="bench.generated.toml")

CLI equivalents for ``colosseum run`` and ``colosseum run-suite``::

   colosseum run my_test.py --autoconfig
   colosseum run my_test.py --autoconfig --autoconfig-export bench.generated.toml
   colosseum run-suite suite.toml --autoconfig --autoconfig-blacklist "Ethernet 1,192.168.1.10"
