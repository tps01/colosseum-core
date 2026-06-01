from __future__ import annotations

import csv
from pathlib import Path


def parse_trace_amplitudes(response: str) -> list[float]:
    text = response.strip()
    if not text:
        return []
    return [float(part.strip()) for part in text.split(",") if part.strip()]


def frequency_axis(center_hz: float, span_hz: float, count: int) -> list[float]:
    if count <= 0:
        return []
    if count == 1:
        return [center_hz]
    start = center_hz - span_hz / 2.0
    step = span_hz / (count - 1)
    return [start + index * step for index in range(count)]


def write_trace_csv(
    path: Path,
    amplitudes_dbm: list[float],
    *,
    center_hz: float | None = None,
    span_hz: float | None = None,
    include_frequency: bool = True,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        if include_frequency and center_hz is not None and span_hz is not None:
            writer = csv.writer(handle)
            writer.writerow(["frequency_hz", "amplitude_dbm"])
            for frequency, amplitude in zip(
                frequency_axis(center_hz, span_hz, len(amplitudes_dbm)),
                amplitudes_dbm,
            ):
                writer.writerow([f"{frequency:.6f}", f"{amplitude:.6f}"])
        else:
            writer = csv.writer(handle)
            writer.writerow(["index", "amplitude_dbm"])
            for index, amplitude in enumerate(amplitudes_dbm):
                writer.writerow([index, f"{amplitude:.6f}"])
