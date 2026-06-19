#!/usr/bin/env python3
"""
Profile unit test execution time (cProfile + pytest --durations).

Backward-compatible alias for ``profile_tests.py --tier unit``.
Prefer ``python scripts/profile_tests.py --tier unit`` for new usage.

Usage (from repo root):
  python scripts/profile_unit_tests.py
  python scripts/profile_unit_tests.py --limit 60 --sort tottime
  python scripts/profile_unit_tests.py --stats build/profile/unit_tests.prof
"""

from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    _scripts = Path(__file__).resolve().parent
    if str(_scripts) not in sys.path:
        sys.path.insert(0, str(_scripts))
    from profile_tests import main

    argv = ["--tier", "unit", *sys.argv[1:]]
    raise SystemExit(main(argv))
