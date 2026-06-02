"""User-facing ``col.io`` namespace (registered by ``colosseum_equipment`` plugin)."""

from colosseum_equipment.io.api import dio, i2c, spi

__all__ = ["dio", "i2c", "spi"]
