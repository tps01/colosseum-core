Quickstart
==========

Core applications are ordinary Python scripts. Installed plugins provide the bench APIs::

   import colosseum as col

   def main():
       col.config.load_config("bench.toml")
       col.acme.measure_value(device_id=1, key="value")
       col.acme.verify_value(key="value", expected_val=10.0)

   if __name__ == "__main__":
       main()
       col.endex()

Run the script directly or through the CLI::

   colosseum run my_test.py --config bench.toml

``col.endex()`` finalizes logs, SQLite evidence, summaries, plugin shutdown hooks, and
the process exit code. Extension authors should start with :doc:`plugins`.
