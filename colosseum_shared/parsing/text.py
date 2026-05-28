from __future__ import annotations

import re
from typing import List, Optional


def strip_response(text: str) -> str:
    return text.strip()


def parse_float(text: str) -> float:
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not match:
        raise ValueError(f"No numeric value in response: {text!r}")
    return float(match.group(0))


def parse_float_list(text: str, sep: str = ",") -> List[float]:
    return [float(part.strip()) for part in text.split(sep) if part.strip()]


def parse_key_value_lines(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def first_match_group(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text)
    return match.group(0) if match else None
