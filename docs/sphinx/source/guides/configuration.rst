Configuration
=============

Bench resources are described in TOML. A section may be a single table or an array of tables; Colosseum normalizes both forms.

Example PSU entry::

   [[equipment.psu]]
   psu_id = 1
   driver = "visa"
   resource = "USB0::0x1234::0x5678::INSTR"
   voltage = 3.3

Plugins register repeatable sections at load time (for example ``equipment.psu``, ``shared.ssh``). Unknown keys in a section log a warning; missing required keys fail when the resource is first used.

For offline development and CI, use ``examples/configs/bench.sim.toml`` with ``driver = "sim"``.
