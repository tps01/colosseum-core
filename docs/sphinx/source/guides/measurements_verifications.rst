Measurements and verifications
================================

Measurements store evidence under a **key** scoped by domain and command. Verifications declare **measurement sources** explicitly; they do not infer evidence from their own function name.

Required verification ``FAIL`` or ``ERROR`` fails the run. Missing measurement for a required verification records ``ERROR``.

Optional verifications may fail without failing the run::

   col.equipment.dmm.verify_voltage(key="probe", expected_val=1.8, tolerance=0.1, optional=True)

Plugin APIs use the ``equipment`` or ``shared`` domain automatically when implemented in ``colosseum_equipment`` or ``colosseum_shared``.
