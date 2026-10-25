"""Duration and frequency values for plugin commands.

Decorated commands, measurements, and verifications parse these parameter
names before the function runs. Numbers are unchanged. Strings use the
suffixes below. A bare number is seconds or hertz, matching the parameter.

Duration names: ``duration``, ``timeout``, ``seconds``, ``seconds_per_div``,
and names ending in ``_s`` (for example ``timeout_s``, ``dwell_s``,
``period_s``). ``expected_s`` and ``position_s`` are signed, so they are left
alone. Names ending in ``_per_s`` are rates, not durations.

Frequency names: ``frequency``, ``span``, ``rbw``, ``vbw``, and names ending
in ``_hz``.
"""

from __future__ import annotations

import re
from math import isfinite
from typing import Any

_DURATION_TOKEN_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)(?P<unit>w|d|h|ms|us|µs|m|s)",
    re.IGNORECASE,
)
_BARE_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")
_FREQUENCY_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)(?:\s*)?(?P<unit>GHz|MHz|kHz|Hz)",
    re.IGNORECASE,
)

_UNIT_SECONDS = {
    "w": 604800.0,
    "d": 86400.0,
    "h": 3600.0,
    "m": 60.0,
    "s": 1.0,
    "ms": 0.001,
    "us": 1e-6,
    "µs": 1e-6,
}
_UNIT_HERTZ = {
    "hz": 1.0,
    "khz": 1e3,
    "mhz": 1e6,
    "ghz": 1e9,
}

_DURATION_NAMES = frozenset({"duration", "timeout", "seconds", "seconds_per_div"})
_SKIP_DURATION_NAMES = frozenset({"expected_s", "position_s"})
_FREQUENCY_NAMES = frozenset({"frequency", "span", "rbw", "vbw"})


def _finite_nonnegative(number: float, original: object, *, kind: str) -> float:
    if not isfinite(number):
        raise ValueError(f"{kind} must be finite, got {original!r}")
    if number < 0:
        raise ValueError(f"{kind} must be non-negative, got {original!r}")
    return number


def parse_duration(duration: float | int | str) -> float:
    """Return a finite, non-negative duration in seconds.

    Bare numbers (``int``, ``float``, or numeric strings) are seconds.
    Unit suffixes follow common Python/timedelta style: ``us``/``µs``, ``ms``,
    ``s``, ``m``, ``h``, ``d``, ``w`` (combinable, e.g. ``1h30m``).
    Zero is allowed. Negative and non-finite values are rejected.
    """
    if isinstance(duration, (int, float)):
        return _finite_nonnegative(float(duration), duration, kind="duration")

    text = duration.strip()
    if not text:
        raise ValueError("duration must not be empty")
    if _BARE_NUMBER_RE.fullmatch(text):
        return _finite_nonnegative(float(text), duration, kind="duration")

    pos = 0
    total = 0.0
    for match in _DURATION_TOKEN_RE.finditer(text):
        if match.start() != pos:
            break
        unit = match.group("unit").lower()
        total += float(match.group("value")) * _UNIT_SECONDS[unit]
        pos = match.end()
    else:
        if pos == len(text) and pos > 0:
            return _finite_nonnegative(total, duration, kind="duration")

    raise ValueError(
        f"Invalid duration {duration!r}; use a number of seconds or "
        "suffixes us/ms/s/m/h/d/w (e.g. 30, 500ms, 1h30m)",
    )


def parse_frequency(frequency: float | int | str) -> float:
    """Return a finite, non-negative frequency in hertz.

    Bare numbers are hertz. Suffixes are ``Hz``, ``kHz``, ``MHz``, and ``GHz``
    (case-insensitive, optional space, e.g. ``1GHz``, ``10 MHz``).
    """
    if isinstance(frequency, bool) or not isinstance(frequency, (int, float, str)):
        raise ValueError(f"Invalid frequency {frequency!r}")
    if isinstance(frequency, (int, float)):
        return _finite_nonnegative(float(frequency), frequency, kind="frequency")

    text = frequency.strip()
    if not text:
        raise ValueError("frequency must not be empty")
    match = _FREQUENCY_RE.fullmatch(text)
    if match is not None:
        hertz = float(match.group("value")) * _UNIT_HERTZ[match.group("unit").lower()]
        return _finite_nonnegative(hertz, frequency, kind="frequency")
    if _BARE_NUMBER_RE.fullmatch(text) or "e" in text.lower():
        try:
            return _finite_nonnegative(float(text), frequency, kind="frequency")
        except ValueError:
            pass
    raise ValueError(
        f"Invalid frequency {frequency!r}; use a number of hertz or "
        "a Hz, kHz, MHz, or GHz suffix (e.g. 1e9, 100kHz, 1 GHz)",
    )


def _is_duration_name(name: str) -> bool:
    if name in _SKIP_DURATION_NAMES or name.endswith("_per_s"):
        return False
    return name in _DURATION_NAMES or name.endswith("_s")


def _is_frequency_name(name: str) -> bool:
    return name in _FREQUENCY_NAMES or name.endswith("_hz")


def coerce_units(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Parse duration and frequency strings in ``kwargs``. Numbers pass through."""
    converted: dict[str, Any] | None = None
    for name, value in kwargs.items():
        if not isinstance(value, str):
            continue
        try:
            if _is_duration_name(name):
                parsed = parse_duration(value)
            elif _is_frequency_name(name):
                parsed = parse_frequency(value)
            else:
                continue
        except ValueError as exc:
            raise ValueError(f"{name}: {exc}") from exc
        if converted is None:
            converted = dict(kwargs)
        converted[name] = parsed
    return kwargs if converted is None else converted
