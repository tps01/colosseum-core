class IoError(Exception):
    """Base error for ``col.io`` operations."""


class IoNotImplementedError(IoError):
    """Raised when a bus driver has not been implemented yet."""
