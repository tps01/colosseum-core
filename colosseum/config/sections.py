from dataclasses import dataclass
from typing import Callable, Tuple


@dataclass(frozen=True)
class ConfigSectionSpec:
    dotted_path: str
    id_field: str
    required_keys: Tuple[str, ...] = ()
    optional_keys: Tuple[str, ...] = ()

    def allowed_keys(self) -> set[str]:
        return {self.id_field, *self.required_keys, *self.optional_keys}


ConfigValidator = Callable[[dict], list[str]]
