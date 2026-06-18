from __future__ import annotations

import re


def strip_response(text: str) -> str:
    """Strip leading and trailing whitespace from instrument response text.

    :param text: Raw response string.
    :type text: str

    :returns: Stripped text.
    :rtype: str
    """
    return text.strip()


def parse_float(text: str) -> float:
    """Parse the first floating-point number from a response string.

    :param text: Raw response text (may contain units or surrounding prose).
    :type text: str

    :returns: Parsed numeric value.
    :rtype: float

    :raises ValueError: When no numeric token is found.
    """
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not match:
        raise ValueError(f"No numeric value in response: {text!r}")
    return float(match.group(0))


def parse_float_list(text: str, sep: str = ",") -> list[float]:
    """Parse a delimiter-separated list of floats from response text.

    :param text: Raw response text containing numeric tokens.
    :type text: str
    :param sep: Field separator (default comma).
    :type sep: str, optional

    :returns: Parsed float values in field order.
    :rtype: list[float]
    """
    return [float(part.strip()) for part in text.split(sep) if part.strip()]


def parse_key_value_lines(text: str) -> dict[str, str]:
    """Parse ``key=value`` lines from multiline instrument output.

    :param text: Raw multiline response text.
    :type text: str

    :returns: Mapping of stripped keys to stripped values (one entry per line with ``=``).
    :rtype: dict[str, str]
    """
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def first_match_group(pattern: str, text: str) -> str | None:
    """Return the first regex match in ``text``, or ``None`` when absent.

    :param pattern: Regular expression searched with :func:`re.search`.
    :type pattern: str
    :param text: Text to search.
    :type text: str

    :returns: Matched substring, or ``None`` when the pattern does not match.
    :rtype: str | None
    """
    match = re.search(pattern, text)
    return match.group(0) if match else None
