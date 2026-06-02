Configuration
=============

Bench resources are described in TOML. A section may be a single table or an array of tables; Colosseum normalizes both forms.

Example PSU entry (``driver`` omitted — defaults to VISA/SCPI)::

   [[equipment.psu]]
   psu_id = 1
   resource = "USB0::0x1234::0x5678::INSTR"
   voltage = 3.3

Example VSG and spectrum analyzer entries::

   [[equipment.vsg]]
   vsg_id = 1
   model = "keysight-esg"
   resource = "GPIB0::19::INSTR"
   frequency = 1e9
   power_dbm = -10.0

   [[equipment.speca]]
   speca_id = 1
   model = "keysight-e4407b"
   resource = "GPIB0::18::INSTR"
   center_freq = 1e9
   span = 10e6
   rbw = 100e3

For lab benches, ``driver`` defaults to ``visa`` (PyVISA + SCPI). Set ``driver = "sim"`` for offline smoke/CI, or ``driver = "serial"`` on ``equipment.serial`` raw port channels.

Plugins register repeatable sections at load time (for example ``equipment.psu``, ``equipment.vsg``, ``equipment.speca``, ``shared.ssh``). Unknown keys in a section log a warning; missing required keys fail when the resource is first used.

Required and optional keys per section (generated from code) are in :doc:`bench_config_reference`. Build the HTML manual with ``python scripts/docgen/build_all.py`` to refresh that page.

For offline development and CI:

* ``examples/configs/bench.sim.toml`` — ``driver = "sim"`` (PSU/DMM cooperative sim)
* ``examples/configs/bench.visa-sim.toml`` — PyVISA-sim for DMM/PSU SCPI
* ``examples/configs/bench.rf.visa-sim.toml`` — PyVISA-sim for VSG and speca (Python 3.10+)

See :doc:`rf_equipment` for RF workflow examples.
