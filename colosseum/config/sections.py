from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ConfigSectionSpec:
    dotted_path: str
    id_field: str
    required_keys: tuple[str, ...] = ()
    optional_keys: tuple[str, ...] = ()

    def allowed_keys(self) -> set[str]:
        return {self.id_field, *self.required_keys, *self.optional_keys}


ConfigValidator = Callable[[dict[str, Any]], list[str]]
