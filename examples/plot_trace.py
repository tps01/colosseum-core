"""
Offline helper: plot a save_trace_data CSV artifact.

Usage:
  python examples/plot_trace.py outputs/<run>/traces/carrier.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

from colosseum_equipment.instruments.speca.trace_plot import write_trace_plot


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python examples/plot_trace.py <trace.csv>")
    trace_path = Path(sys.argv[1])
    out_path = trace_path.with_suffix(".png")
    write_trace_plot(trace_path, out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
