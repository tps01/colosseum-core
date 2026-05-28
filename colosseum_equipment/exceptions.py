class EquipmentError(RuntimeError):
    pass


class EquipmentConnectionError(EquipmentError):
    pass


class EquipmentTimeoutError(EquipmentError):
    pass


class EquipmentResponseError(EquipmentError):
    pass
