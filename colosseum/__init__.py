"""Colosseum public API."""

from . import config, database
from .decorators import (
    CommandResult,
    MeasurementSource,
    VerificationResult,
    command,
    measurement,
    verification,
)
from .plugins.namespace import LazyNamespaceProxy
from .results import endex

__version__ = "0.12.0"

equipment = LazyNamespaceProxy("equipment")
shared = LazyNamespaceProxy("shared")
io = LazyNamespaceProxy("io")
host = LazyNamespaceProxy("host")

__all__ = [
    "__version__",
    "config",
    "database",
    "command",
    "measurement",
    "verification",
    "CommandResult",
    "MeasurementSource",
    "VerificationResult",
    "endex",
    "equipment",
    "shared",
    "io",
    "host",
]
