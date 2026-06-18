Measurements, commands, and verifications
==========================================

Colosseum records three kinds of decorated API calls in ``execution.sqlite`` and
``debug.log``.

Commands
--------

Use ``@command`` for setup and action APIs (PSU ``set_voltage``, VSG ``play_iq``,
``col.io.dio.write_pin``, ``col.host.config.capture_host_profile``, and similar).
Commands are **not** verifications; a required command ``ERROR`` or ``FAIL`` still
fails the run at ``col.endex()``.

``key=`` is **optional**. When omitted, the command row uses an empty key. Each
invocation appends a new row (no duplicate-key rejection). Use ``optional=True`` to
record a failure without failing the aggregate result.

On exception, the command wrapper records ``ERROR``, logs the traceback, and returns
``None`` so the script can continue to ``col.endex()``.

Measurements
------------

Measurements store evidence under a **key** scoped by domain and command. Duplicate
keys for the same domain and command raise an error.

Equipment domain and keys
~~~~~~~~~~~~~~~~~~~~~~~~~

All ``col.equipment.*`` and ``col.io.*`` APIs share SQLite domain ``equipment``. The
command name includes the public API group, such as ``dmm.measure_voltage``,
``psu.measure_voltage``, or ``io.dio.read_port``. Use a unique key per
``(domain, command)`` pair. Tolerance verifiers such as ``col.equipment.dmm.verify_voltage``
look up the matching grouped measurement command, such as ``dmm.measure_voltage``.

Verifications
-------------

Verifications declare **measurement sources** explicitly; they do not infer evidence
from their own function name.

Required verification ``FAIL`` or ``ERROR`` fails the run. Missing measurement for a
required verification records ``ERROR``.

Optional verifications may fail without failing the run::

   col.equipment.dmm.verify_voltage(key="probe", expected_val=1.8, tolerance=0.1, optional=True)

Domains
-------

Plugin APIs map to SQLite domains automatically:

- ``colosseum_equipment`` and ``colosseum_equipment.io`` → ``equipment`` (including ``col.io.*``)
- ``colosseum_shared`` → ``shared``
- ``colosseum_host`` → ``host``

Extension authors import ``command``, ``measurement``, and ``verification`` from
``colosseum.decorators``.
