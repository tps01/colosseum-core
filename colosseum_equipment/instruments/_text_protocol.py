"""Helpers for line-oriented instrument protocols (non-SCPI)."""

from __future__ import annotations

import re


def parse_adaura_status_channel(response: str, channel: int) -> float:
    """Parse ``STATUS`` output line ``Channel N: <dB>``."""
    pattern = re.compile(rf"Channel\s+{channel}\s*:\s*([0-9.+-]+)", re.IGNORECASE)
    match = pattern.search(response)
    if not match:
        raise ValueError(f"channel {channel} not found in STATUS response: {response!r}")
    return float(match.group(1))
