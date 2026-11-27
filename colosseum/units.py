"""Parse unit-bearing inputs for decorated plugin APIs.

Bare numbers retain the unit of their argument. Core infers seconds or hertz
from recognized argument names by default. Plugins can declare input units explicitly.
"""

from __future__ import annotations

import re
from math import isfinite
from typing import Any, Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])
_NUMBER = r"(?P<mantissa>[+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:[eE](?P<exponent>[+-]?\d+))?"
_QUANTITY = re.compile(rf"{_NUMBER}\s*(?P<unit>\S*)")
_DURATION_TOKEN = re.compile(rf"\s*{_NUMBER}\s*(?P<unit>ps|ns|us|µs|μs|ms|w|d|h|m|s)")
_PREFIX_EXPONENTS = {"p": -12, "n": -9, "u": -6, "µ": -6, "μ": -6, "m": -3, "k": 3, "M": 6, "G": 9, "T": 12}
_DURATION_SCALES = {"w": 604800, "d": 86400, "h": 3600, "m": 60}
_PREFIXABLE = frozenset({"Hz", "V", "A", "W", "Ω", "m", "A/s", "V/s", "V/div"})
_DURATION_NAMES = frozenset({"duration", "timeout", "seconds", "seconds_per_div"})
_SKIP_DURATION_NAMES = frozenset({"expected_s", "position_s"})
_FREQUENCY_NAMES = frozenset({"frequency", "span", "rbw", "vbw"})


def unit_inputs(**units: str) -> Callable[[_F], _F]:
    """Declare the base units of named arguments to a Colosseum decorator.

    Apply this below ``@command``, ``@measurement``, or ``@verification``.
    For example, ``@unit_inputs(voltage="V")`` converts a voltage string to volts.
    """
    def declare(func: _F) -> _F:
        func.__dict__["_colosseum_input_units"] = units
        return func

    return declare


def _number(match: re.Match[str], offset: int = 0) -> float:
    exponent = int(match["exponent"] or "0") + offset
    return float(f"{match['mantissa']}e{exponent}")


def _checked(number: float, original: object, *, kind: str, nonnegative: bool = False) -> float:
    if not isfinite(number):
        raise ValueError(f"{kind} must be finite, got {original!r}")
    if nonnegative and number < 0:
        raise ValueError(f"{kind} must be non-negative, got {original!r}")
    return number


def _parse_quantity(value: str, unit: str, *, nonnegative: bool = False) -> float:
    expected = "Ω" if unit in {"ohm", "R"} else unit
    match = _QUANTITY.fullmatch(value.strip())
    if match is not None:
        suffix = match["unit"]
        if expected == "Ω":
            suffix = suffix.replace("ohm", "Ω").replace("R", "Ω")
        offset: int | None
        if suffix in ("", expected):
            offset = 0
        elif expected in _PREFIXABLE and suffix.endswith(expected):
            offset = _PREFIX_EXPONENTS.get(suffix[:-len(expected)])
        else:
            offset = None
        if offset is not None:
            return _checked(_number(match, offset), value, kind=unit, nonnegative=nonnegative)
    label = "frequency" if unit == "Hz" else unit
    raise ValueError(f"Invalid {label} {value!r}; expected a number or a quantity in {unit}")


def parse_duration(duration: float | int | str) -> float:
    """Return seconds from a number or a lowercase duration such as ``10 ms`` or ``1h30m``."""
    if isinstance(duration, (int, float)):
        return _checked(float(duration), duration, kind="duration", nonnegative=True)
    text = duration.strip()
    if not text:
        raise ValueError("duration must not be empty")
    bare = _QUANTITY.fullmatch(text)
    if bare is not None and not bare["unit"]:
        return _checked(_number(bare), duration, kind="duration", nonnegative=True)

    pos = 0
    total = 0.0
    for match in _DURATION_TOKEN.finditer(text):
        if match.start() != pos:
            break
        unit = match["unit"]
        if unit in _DURATION_SCALES:
            number = _number(match) * _DURATION_SCALES[unit]
        else:
            number = _number(match, _PREFIX_EXPONENTS.get(unit[:-1], 0))
        total += _checked(number, duration, kind="duration", nonnegative=True)
        pos = match.end()
    if pos == len(text):
        return _checked(total, duration, kind="duration", nonnegative=True)
    raise ValueError(f"Invalid duration {duration!r}; use seconds or ps/ns/us/ms/s/m/h/d/w (e.g. 10 ms, 1h30m)")


def parse_frequency(frequency: float | int | str) -> float:
    """Return hertz from a number or a case-sensitive quantity such as ``10e3kHz``."""
    if isinstance(frequency, bool) or not isinstance(frequency, (int, float, str)):
        raise ValueError(f"Invalid frequency {frequency!r}")
    if isinstance(frequency, (int, float)):
        return _checked(float(frequency), frequency, kind="frequency", nonnegative=True)
    if not frequency.strip():
        raise ValueError("frequency must not be empty")
    return _parse_quantity(frequency, "Hz", nonnegative=True)


def _is_duration_name(name: str) -> bool:
    if name in _SKIP_DURATION_NAMES or name.endswith("_per_s"):
        return False
    return name in _DURATION_NAMES or name.endswith("_s")


def _is_frequency_name(name: str) -> bool:
    return name in _FREQUENCY_NAMES or name.endswith("_hz")


def coerce_units(kwargs: dict[str, Any], *, func: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Parse quantity strings using declared units or default inference by argument name."""
    declared = getattr(func, "_colosseum_input_units", {})
    converted: dict[str, Any] | None = None
    for name, value in kwargs.items():
        if not isinstance(value, str):
            continue
        try:
            unit = declared.get(name)
            if unit == "s" or (unit is None and _is_duration_name(name)):
                parsed = parse_duration(value)
            elif unit == "Hz" or (unit is None and _is_frequency_name(name)):
                parsed = parse_frequency(value)
            elif unit is not None:
                parsed = _parse_quantity(value, unit)
            else:
                continue
        except ValueError as exc:
            raise ValueError(f"{name}: {exc}") from exc
        if converted is None:
            converted = dict(kwargs)
        converted[name] = parsed
    return kwargs if converted is None else converted
