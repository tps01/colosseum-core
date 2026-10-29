Quickstart
==========

Run a first test without hardware. This **evidence recording demonstration**
records a literal voltage and verifies it; it does not read an instrument.

1. Install core and Shared
--------------------------

Download the compatible core and Shared wheels from their GitHub Releases
(see :doc:`installation`). Install both in the same virtual environment,
substituting the downloaded filenames::

   python -m pip install ./colosseum_core-<version>-py3-none-any.whl
   python -m pip install ./colosseum_shared-<version>-py3-none-any.whl
   colosseum --help

2. Create a test
----------------

In an empty directory, save **my_test.py**::

   import colosseum as col

   def main() -> None:
       col.shared.measure_value(key="voltage", value=3.3)
       col.shared.verify.verify_field(key="voltage", expected_val=3.3, tolerance=0.1)

The CLI calls ``main()`` and finalizes the run when it returns. Under the CLI
you do not need ``col.endex()``. Direct Python execution is covered in
:doc:`writing_test_scripts`.

3. Create a config
------------------

Save **config.toml** containing only this comment::

   # Shared literal measurements need no device configuration.

A comment-only TOML file is valid. It gives the runner a config path without
introducing instrument or report settings.

4. Run and inspect the result
-----------------------------

From the directory containing those two files::

   colosseum run my_test.py -g config.toml

The run exits 0. Open ``summary.txt`` in ``outputs/<timestamp>_my_test-pass/``.
Its fields include::

   Overall result: PASS
   Exit code: 0
   Measurements: 1

There is one required PASS verification. Change ``expected_val`` to ``5.0`` and
run the same command again. This run exits 1 and writes a ``-fail`` folder;
the summary shows ``Overall result: FAIL`` and lists ``voltage`` under
``Failed required outcomes``. A failed verification still lets later steps run.

Each run also writes ``debug.log`` (diagnostics), ``execution.sqlite`` (recorded
evidence), and ``summary.json`` (machine-readable results). Reports are optional;
see :doc:`output_artifacts`.

5. Next steps
-------------

* API details: `measure_value <https://tps01.github.io/colosseum-shared/api/measure_value.html>`__
  and `verify_field <https://tps01.github.io/colosseum-shared/api/verify.html#colosseum_shared.verify.api.verify_field>`__.
* Evidence keys and failures: :doc:`measurements_verifications`.
* Write and parameterize scripts: :doc:`writing_test_scripts` and :doc:`using_parameters`.
* Select APIs by task: :doc:`first_party_plugins`.
* Run suites: :doc:`running_suites`.

This page works in a standalone directory. Commands elsewhere that start with
``examples/`` require files from the named package's repository checkout.
