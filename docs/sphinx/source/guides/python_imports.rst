Python import behavior in suites
================================

While the script runs, the runner puts the script directory first on
``sys.path`` (the same as ``python my_test.py``), so sibling helpers in that
directory import cleanly. After the script returns or raises, ``sys.path`` is
restored. Sibling modules stay in ``sys.modules`` for the process, so suite
setup and later tests share the same helper state. A multi-directory suite is
still one process: the same helper basename in two folders reuses the first
import. Names that collide with an already-imported module, or with a stdlib or
plugin name, resolve the same way as a direct Python launch.


Use a uniquely named helper package for shared suite state. Avoid two unrelated
``helpers.py`` modules in different test directories: the first imported module
can be reused by later slots. Configuration and connection lifetimes are
separate from Python module caching; see :doc:`running_suites`.
