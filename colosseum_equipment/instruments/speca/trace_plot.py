from __future__ import annotations

import csv
from pathlib import Path


def read_trace_csv(path: Path) -> tuple[list[float], list[float]]:
    frequencies: list[float] = []
    amplitudes: list[float] = []
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if "frequency_hz" in row and row["frequency_hz"]:
                frequencies.append(float(row["frequency_hz"]))
            if "amplitude_dbm" in row:
                amplitudes.append(float(row["amplitude_dbm"]))
            elif "value" in row:
                amplitudes.append(float(row["value"]))
    if not amplitudes:
        raise ValueError(f"trace CSV is empty: {path}")
    return frequencies, amplitudes


def write_trace_plot(csv_path: Path, plot_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is required for spectrum trace plots. "
            "Install with: pip install colosseum[plot]"
        ) from exc

    frequencies, amplitudes = read_trace_csv(csv_path)
    x_values = frequencies if frequencies else list(range(len(amplitudes)))
    x_label = "Frequency (Hz)" if frequencies else "Index"
    y_label = "Amplitude (dBm)" if frequencies else "Value"

    plot_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(8, 4))
    try:
        axis.plot(x_values, amplitudes)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)
        axis.grid(True, alpha=0.3)
        figure.savefig(plot_path, dpi=120, bbox_inches="tight")
    finally:
        plt.close(figure)
