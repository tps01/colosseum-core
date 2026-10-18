"""Core runtime exceptions."""

from __future__ import annotations


class ProceduralFault(RuntimeError):
    """The procedure could not be carried out.

    Raised when a resource never opens, a parameters file cannot be read, or
    another break stops the planned measurement before it can be taken. A DUT
    that stays silent is not a procedural fault.
    """
