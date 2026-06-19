"""
Backward-compatible re-exports for profile_unit_tests.py.

Prefer ``pytest_profiler.profile_pytest`` for new code.
"""

from __future__ import annotations

from pytest_profiler import ProfileReport, profile_pytest, profile_pytest_unit_tests

__all__ = ("ProfileReport", "profile_pytest", "profile_pytest_unit_tests")
