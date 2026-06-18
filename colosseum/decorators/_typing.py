"""Typing backports for supported Python versions."""

from __future__ import annotations

import sys

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

__all__ = ["ParamSpec"]
