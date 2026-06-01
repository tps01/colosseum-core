class EquipmentError(RuntimeError):
    pass


class EquipmentConnectionError(EquipmentError):
    pass


class EquipmentTimeoutError(EquipmentError):
    pass


class EquipmentResponseError(EquipmentError):
    pass


class EquipmentCapabilityError(EquipmentError):
    """Raised when a high-level API is not supported by the configured model."""
