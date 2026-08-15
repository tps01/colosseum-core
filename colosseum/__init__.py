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

__version__ = "0.15.0"

equipment = LazyNamespaceProxy("equipment")
shared = LazyNamespaceProxy("shared")
io = LazyNamespaceProxy("io")
host = LazyNamespaceProxy("host")


def __getattr__(name: str) -> LazyNamespaceProxy:
    """Resolve third-party plugin namespaces (e.g. ``col.acme.*``) after install."""
    if name.startswith("_"):
        raise AttributeError(name)
    return LazyNamespaceProxy(name)


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
