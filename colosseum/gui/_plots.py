"""Limit and XY views drawn by the GUI on a Tk canvas.

Axes come only from recorded comparisons or a series that declares x, y, and
units. Core does not depend on a plotting library for these views.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Optional

Point = tuple[Optional[float], Optional[float]]


@dataclass(frozen=True)
class LimitView:
    actual: float
    low: float | None
    high: float | None
    units: str


@dataclass(frozen=True)
class XySeries:
    points: list[Point]
    x_unit: str
    y_unit: str


def limit_view(
    *,
    compare_op: str,
    expected_raw: str,
    tolerance_raw: str,
    actual_raw: str,
    units: str,
) -> LimitView | None:
    """A numeric limit graphic, or None when the comparison is not a plain range."""
    actual = _number(_parse(actual_raw))
    expected = _number(_parse(expected_raw))
    if actual is None or expected is None:
        return None
    op = compare_op.upper()
    if op == "EQ":
        return LimitView(actual=actual, low=expected, high=expected, units=units)
    if op == "GE":
        return LimitView(actual=actual, low=expected, high=None, units=units)
    if op == "LE":
        return LimitView(actual=actual, low=None, high=expected, units=units)
    if op != "GELE":
        return None
    tolerance = _number(_parse(tolerance_raw))
    if tolerance is None or tolerance < 0:
        return None
    return LimitView(
        actual=actual,
        low=expected - tolerance,
        high=expected + tolerance,
        units=units,
    )


def limit_window(low: float | None, high: float | None) -> tuple[float, float]:
    """Numeric ends of the number line. The measured value does not change the zoom.

    A two-sided band fills the middle 60%. A minimum stays at 25% and a maximum
    at 75%. Equal limits stay centered in a window 40% as wide as their magnitude.
    """
    if low is not None and high is not None and low != high:
        if low > high:
            low, high = high, low
        pad = (high - low) / 3
        return low - pad, high + pad
    anchor = low if low is not None else high
    if anchor is None:
        return -1.0, 1.0
    span = _magnitude_span(anchor)
    if low is not None and high is not None:
        return anchor - span / 2, anchor + span / 2
    if low is not None:
        return anchor - span * 0.25, anchor + span * 0.75
    return anchor - span * 0.75, anchor + span * 0.25


def limit_fraction(value: float, low: float | None, high: float | None) -> float:
    """Position from 0 to 1. Values outside the stable window pin to the ends."""
    left, right = limit_window(low, high)
    if right == left:
        return 0.5
    fraction = (value - left) / (right - left)
    if fraction < 0.0:
        return 0.0
    if fraction > 1.0:
        return 1.0
    return fraction


def _magnitude_span(anchor: float) -> float:
    magnitude = abs(anchor)
    if magnitude == 0:
        return 1.0
    return magnitude * 0.4


def explicit_xy(value: object) -> XySeries | None:
    """XY data only when x, y, and both units are declared. A bare array is not a trace."""
    parsed = value
    if isinstance(value, str):
        parsed = _parse(value)
    if not isinstance(parsed, dict):
        return None
    if not {"x", "y", "x_unit", "y_unit"} <= set(parsed):
        return None
    x_unit = parsed.get("x_unit")
    y_unit = parsed.get("y_unit")
    if not isinstance(x_unit, str) or not isinstance(y_unit, str):
        return None
    if not x_unit or not y_unit:
        return None
    points = _pair(parsed.get("x"), parsed.get("y"))
    if points is None:
        return None
    return XySeries(points=points, x_unit=x_unit, y_unit=y_unit)


def reduce_xy(
    points: list[Point],
    *,
    low: float | None,
    high: float | None,
    max_points: int,
) -> list[Point]:
    """Shorten a trace without dropping a sample that sits outside the limit."""
    if max_points < 2 or len(points) <= max_points:
        return list(points)
    bucket_count = max(1, max_points // 3)
    width = max(1, math.ceil(len(points) / bucket_count))
    reduced: list[Point] = []
    for start in range(0, len(points), width):
        bucket = points[start : start + width]
        finite = [
            (index, x, y)
            for index, (x, y) in enumerate(bucket)
            if x is not None and y is not None
        ]
        if not finite:
            reduced.append((None, None))
            continue
        keep = {finite[0][0], finite[-1][0]}
        min_index = min(finite, key=lambda item: item[2])[0]
        max_index = max(finite, key=lambda item: item[2])[0]
        keep.add(min_index)
        keep.add(max_index)
        for index, _x, y in finite:
            if _outside(y, low, high):
                keep.add(index)
        for index in sorted(keep):
            reduced.append(bucket[index])
    return reduced


def _pair(x_values: object, y_values: object) -> list[Point] | None:
    if not isinstance(x_values, list) or not isinstance(y_values, list):
        return None
    if len(x_values) != len(y_values) or not x_values:
        return None
    points: list[Point] = []
    for x_value, y_value in zip(x_values, y_values):
        x_number = _sample(x_value)
        y_number = _sample(y_value)
        if x_number is False or y_number is False:
            return None
        points.append((x_number, y_number))
    return points


def _sample(value: object) -> float | None | bool:
    """Return a coordinate, None for a gap, or False when the value is not numeric."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and math.isnan(value):
        return None
    return float(value)


def _outside(value: float, low: float | None, high: float | None) -> bool:
    if low is not None and value < low:
        return True
    return high is not None and value > high


def _parse(value: str) -> object:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return float(value)
