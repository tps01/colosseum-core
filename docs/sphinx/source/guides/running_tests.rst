Running test cases
==================

**Direct Python:** ``python my_test.py`` after ``col.config.load_config(...)`` and ``col.endex()`` in ``__main__``.

**CLI:** ``colosseum run my_test.py --config bench.toml`` initializes the runtime, calls ``main()``, then ``col.endex()``.

**Utility mode (no persisted evidence):** use ``--no-artifacts`` on the CLI, ``col.config.load_config(path, no_artifacts=True)`` in a script, or set ``COLOSSEUM_NO_ARTIFACTS=1``. Console logging and in-memory SQLite remain available; ``outputs/``, ``debug.log``, on-disk ``execution.sqlite``, and summary files are not created. APIs that write files under the run directory (for example ``col.equipment.speca.save_trace_data``) require persisted output and fail in no-artifacts mode.

To scan VISA resources instead of a bench file, use ``--autoconfig`` (requires ``colosseum[hardware]``)::

   colosseum run my_test.py --autoconfig
   colosseum run my_test.py --autoconfig --autoconfig-export bench.generated.toml

The CLI does not execute the script's ``if __name__ == "__main__"`` block; only ``main()`` is invoked.

Output is written lazily under ``outputs/<timestamp>_<test_stem>/`` as ``debug.log``, ``execution.sqlite``, and ``summary.txt``.

INFO-level log lines (including run header metadata and measurement/verification summaries) are echoed to stdout. Use ``-d`` or ``--debug`` to include DEBUG on stdout as well; ``debug.log`` always records DEBUG.
