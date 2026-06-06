from __future__ import annotations


def _smooth(values: list[float], order: int) -> list[float]:
    if order <= 0 or len(values) < 2:
        return list(values)
    order * 2 + 1
    smoothed: list[float] = []
    for index in range(len(values)):
        start = max(0, index - order)
        end = min(len(values), index + order + 1)
        segment = values[start:end]
        smoothed.append(sum(segment) / len(segment))
    return smoothed


def _crossing_frequency(
    frequencies_hz: list[float],
    amplitudes_dbm: list[float],
    *,
    start_index: int,
    step: int,
    threshold_dbm: float,
) -> float:
    index = start_index
    while 0 <= index < len(amplitudes_dbm):
        if amplitudes_dbm[index] <= threshold_dbm:
            if step > 0 and index > 0:
                left = index - 1
                f0, f1 = frequencies_hz[left], frequencies_hz[index]
                a0, a1 = amplitudes_dbm[left], amplitudes_dbm[index]
                if a1 != a0:
                    ratio = (threshold_dbm - a0) / (a1 - a0)
                    return f0 + ratio * (f1 - f0)
            if step < 0 and index < len(amplitudes_dbm) - 1:
                right = index + 1
                f0, f1 = frequencies_hz[index], frequencies_hz[right]
                a0, a1 = amplitudes_dbm[index], amplitudes_dbm[right]
                if a1 != a0:
                    ratio = (threshold_dbm - a0) / (a1 - a0)
                    return f0 + ratio * (f1 - f0)
            return frequencies_hz[index]
        index += step
    return frequencies_hz[max(0, min(len(frequencies_hz) - 1, index - step))]


def measure_bandwidth_hz(
    frequencies_hz: list[float],
    amplitudes_dbm: list[float],
    *,
    start_hz: float,
    stop_hz: float,
    threshold_db: float = 3.0,
    smoothing_order: int = 0,
) -> float:
    if len(frequencies_hz) != len(amplitudes_dbm):
        raise ValueError("frequency and amplitude arrays must have equal length")
    if start_hz > stop_hz:
        raise ValueError("start_hz must be <= stop_hz")

    band_freqs: list[float] = []
    band_amps: list[float] = []
    for frequency, amplitude in zip(frequencies_hz, amplitudes_dbm):
        if start_hz <= frequency <= stop_hz:
            band_freqs.append(frequency)
            band_amps.append(amplitude)

    if not band_freqs:
        raise ValueError("no trace points in the requested frequency band")

    smoothed = _smooth(band_amps, smoothing_order)
    peak_index = max(range(len(smoothed)), key=lambda index: smoothed[index])
    peak_dbm = smoothed[peak_index]
    threshold_dbm = peak_dbm - threshold_db

    left_hz = _crossing_frequency(
        band_freqs,
        smoothed,
        start_index=peak_index,
        step=-1,
        threshold_dbm=threshold_dbm,
    )
    right_hz = _crossing_frequency(
        band_freqs,
        smoothed,
        start_index=peak_index,
        step=1,
        threshold_dbm=threshold_dbm,
    )
    return max(0.0, right_hz - left_hz)
