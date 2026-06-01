"""
Offline helper: plot a save_trace_data CSV artifact (optional matplotlib).

Usage:
  python examples/plot_trace.py outputs/<run>/traces/carrier.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python examples/plot_trace.py <trace.csv>")
    trace_path = Path(sys.argv[1])
    frequencies: list[float] = []
    amplitudes: list[float] = []
    with trace_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if "frequency_hz" in row:
                frequencies.append(float(row["frequency_hz"]))
            amplitudes.append(float(row["amplitude_dbm"]))

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit("matplotlib required for plotting: pip install matplotlib") from exc

    x_values = frequencies if frequencies else list(range(len(amplitudes)))
    x_label = "Frequency (Hz)" if frequencies else "Index"
    plt.figure(figsize=(8, 4))
    plt.plot(x_values, amplitudes)
    plt.xlabel(x_label)
    plt.ylabel("Amplitude (dBm)")
    plt.grid(True, alpha=0.3)
    out_path = trace_path.with_suffix(".png")
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
