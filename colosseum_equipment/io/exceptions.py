class IoError(Exception):
    """Base error for ``col.io`` operations."""


class IoNotImplementedError(IoError):
    """Raised when a bus driver has not been implemented yet."""


class IoConfigError(IoError):
    """Raised when bench IO configuration is invalid or incomplete."""


class IoConnectionError(IoError):
    """Raised when an IO backend cannot open or communicate with hardware."""
