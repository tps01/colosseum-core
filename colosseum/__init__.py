"""Colosseum public API."""

from . import config
from . import database
from .decorators import MeasurementSource, VerificationResult, measurement, verification
from .plugins.namespace import LazyNamespaceProxy
from .results import endex

__version__ = "0.3.0"

equipment = LazyNamespaceProxy("equipment")
shared = LazyNamespaceProxy("shared")

__all__ = [
    "__version__",
    "config",
    "database",
    "measurement",
    "verification",
    "MeasurementSource",
    "VerificationResult",
    "endex",
    "equipment",
    "shared",
]
