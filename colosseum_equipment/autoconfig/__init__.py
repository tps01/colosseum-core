"""VISA autoconfig: scan, classify, and build bench equipment config."""

from .discovery import AutoconfigResult, discover_equipment_config

__all__ = ["AutoconfigResult", "discover_equipment_config"]
