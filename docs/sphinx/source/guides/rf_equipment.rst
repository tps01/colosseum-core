RF equipment (VSG, ASG, spectrum analyzer, RTSA, VNA)
=======================================================

Colosseum exposes RF bench instruments through ``col.equipment.vsg`` (vector/signal generator),
``col.equipment.asg`` (analog signal generator), ``col.equipment.speca`` (classic spectrum analyzer),
``col.equipment.rtsa`` (real-time spectrum analyzer / IQ acquisition), and ``col.equipment.vna``.

Configure instruments in TOML (see :doc:`configuration` and the generated **Bench configuration reference**).
Select vendor behavior with ``model``. Per-function parameters and return types are documented in Python
docstrings and the generated API reference (``colosseum_equipment.api.vsg``, ``asg``, ``speca``, ``rtsa``, ``vna``).

Supported vendor models
-----------------------

* ``keysight-esg`` — Agilent/Keysight E4428C (analog) and E4438C (vector arb)
* ``keysight-e4407b`` — Agilent/Keysight E4407B ESA-E spectrum analyzer
* ``tektronix-rsa5100b`` — Tektronix RSA5100B RTSA (configure under ``equipment.rtsa``)
* ``generic`` — Keysight-style SCPI for offline PyVISA-sim or compatible lab gear

Example workflows
-----------------

* CW stimulus and swept spectrum: ``examples/test_rf_sweep.py`` (uses ``bench.rf.visa-sim.toml`` or hardware config)
* Vector arb and RTSA capture: ``examples/test_rf_vector_mod.py``
* Max-hold trace capture: ``examples/test_rf_bench_integration.py``
* Offline trace plot: ``python examples/plot_trace.py outputs/<run>/traces/carrier.csv``

Offline CI without hardware uses ``examples/configs/bench.rf.visa-sim.toml`` and ``pytest -m visa_sim``.
Hardware template: ``examples/configs/bench.rf.hardware.toml.example``.

Trace and capture artifacts
---------------------------

``save_trace_data`` on ``col.equipment.speca`` writes a CSV under the active output directory and registers an
artifact row. Pass ``save_plot=True`` or ``plot_path=`` for an optional PNG (``speca_trace_plot``);
install ``colosseum[plot]`` for matplotlib-backed plot generation. RTSA IQ capture uses
``save_IQ_data`` (see API docstrings).

Capability errors
-----------------

If a function is not implemented for the configured ``model``, the driver raises
``EquipmentCapabilityError``. Use ``col.equipment.scpi.write`` / ``query`` with exactly one instrument
``*_id`` for bespoke SCPI.

API reference
-------------

Generated pages under **API reference → Colosseum Equipment** list module docstrings for all public
``col.equipment.*`` RF APIs.
