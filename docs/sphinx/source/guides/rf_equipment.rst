RF equipment (VSG and spectrum analyzer)
==========================================

Colosseum exposes RF bench instruments through ``col.equipment.vsg`` (vector/signal generator) and ``col.equipment.speca`` (spectrum analyzer, including Tektronix RTSA models).

Configure instruments in TOML with ``equipment.vsg`` / ``vsg_id`` and ``equipment.speca`` / ``speca_id``. Select vendor behavior with ``model`` (see :doc:`configuration`).

Supported vendor models:

* ``keysight-esg`` — Agilent/Keysight E4428C (analog) and E4438C (vector arb)
* ``keysight-e4407b`` — Agilent/Keysight E4407B ESA-E spectrum analyzer
* ``tektronix-rsa5100b`` — Tektronix RSA5100B RTSA (Spectrum view + capture download)
* ``generic`` — Keysight-style SCPI for offline PyVISA-sim or compatible lab gear

CW stimulus and swept spectrum (Wave A)
---------------------------------------

Example (one ``col.*`` call per line, matching ``examples/test_rf_sweep.py``)::

   col.equipment.vsg.set_frequency(vsg_id=1, frequency=1e9)
   col.equipment.vsg.set_power(vsg_id=1, power_dbm=-10.0)
   col.equipment.vsg.set_output(vsg_id=1, enabled=True)
   col.equipment.speca.set_center_frequency(speca_id=1, frequency=1e9)
   col.equipment.speca.set_span(speca_id=1, span=10e6)
   col.equipment.speca.set_rbw(speca_id=1, rbw=100e3)
   col.equipment.speca.peak_search(speca_id=1, marker=1)
   col.equipment.speca.measure_marker_power(speca_id=1, marker=1, key="carrier_power")
   col.equipment.speca.save_trace_data(speca_id=1, path="traces/carrier.csv")

Marker at a fixed frequency and verification::

   col.equipment.speca.set_marker_frequency(speca_id=1, marker=1, frequency_hz=1e9)
   col.equipment.speca.measure_marker_power(speca_id=1, marker=1, key="marker_power_1ghz")
   col.equipment.speca.verify_marker_power(key="marker_power_1ghz", expected_val=-42.5, tolerance=0.5)

Trace CSV lookup (nearest frequency bin) after ``save_trace_data``::

   col.equipment.speca.measure_trace_power_at_frequency(speca_id=1, frequency_hz=1e9, key="trace_power_1ghz")
   col.equipment.speca.verify_trace_power_at_frequency(key="trace_power_1ghz", expected_val=-42.5, tolerance=0.5)

Max-hold example: ``set_trace_mode(speca_id=1, trace=1, mode="MAXH")`` with continuous sweep and a dwell before ``save_trace_data``. See ``examples/test_rf_bench_integration.py``.

Offline CI without hardware uses ``examples/configs/bench.rf.visa-sim.toml`` and ``pytest -m visa_sim``. Hardware template: ``examples/configs/bench.rf.hardware.toml.example``.

Trace and capture artifacts
---------------------------

``save_trace_data`` writes a CSV under the active output directory (``frequency_hz,amplitude_dbm`` when ``include_frequency=True``) and registers an artifact row. RTSA-only helpers such as ``download_capture`` and ``save_spectrogram`` require ``model = "tektronix-rsa5100b"``.

Plot a saved trace offline with ``python examples/plot_trace.py outputs/<run>/traces/carrier.csv`` (requires matplotlib).

Capability errors
-------------------

If a function is not implemented for the configured ``model``, the driver raises ``EquipmentCapabilityError``. For example, ``upload_waveform`` on ``model = "generic"``, or ``download_capture`` on ``keysight-e4407b``. Use ``col.equipment.scpi.write`` / ``query`` with ``vsg_id=`` or ``speca_id=`` for bespoke SCPI.

Vector arb and RTSA capture (Wave B)
------------------------------------

See ``examples/test_rf_vector_mod.py`` for ``upload_waveform``, ``select_waveform``, ``set_arb_state``, and ``download_capture``. E4438C vector arb upload requires ``keysight-esg`` with an E4438C ``*IDN?`` response.

API reference
-------------

Generated pages under **API reference → Colosseum Equipment** list ``colosseum_equipment.api.vsg`` and ``colosseum_equipment.api.speca``. Design detail: ``docs/design/ddd-equipment-vsg-speca.md``.
