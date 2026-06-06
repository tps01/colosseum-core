"""User-facing ``col.io`` namespace (registered by ``colosseum_equipment`` plugin)."""

from . import dio, i2c, spi

__all__ = ["dio", "i2c", "spi"]
