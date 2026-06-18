Running test cases
==================

**Direct Python:** ``python my_test.py`` after ``col.config.load_config(...)`` and ``col.endex()`` in ``__main__``.

**CLI:** ``colosseum run my_test.py --config bench.toml`` initializes the runtime, calls ``main()``, then ``col.endex()``.

The CLI does not execute the script's ``if __name__ == "__main__"`` block; only ``main()`` is invoked.

Output is written lazily under ``outputs/<timestamp>_<test_stem>/`` as ``debug.log``, ``execution.sqlite``, and ``summary.txt``.

INFO-level log lines (including run header metadata and measurement/verification summaries) are echoed to stdout. Use ``-d`` or ``--debug`` to include DEBUG on stdout as well; ``debug.log`` always records DEBUG.
