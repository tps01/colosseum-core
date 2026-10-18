from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigSectionSpec:
    """Declare one config TOML section owned by a plugin.

    Each spec has exactly one dotted table path, exactly one integer ID field,
    and any number of required or optional keys (including none of either).
    Register another spec to own a second table type.

    :param dotted_path: TOML table path (for example ``acme.device``).
    :type dotted_path: str
    :param id_field: Integer row identity key (for example ``device_id``).
    :type id_field: str
    :param required_keys: Keys checked for non-empty values when ``require_item`` is called.
    :type required_keys: tuple[str, ...], optional
    :param optional_keys: Additional documented keys. Unknown plugin-row keys
        are preserved without a core warning.
    :type optional_keys: tuple[str, ...], optional
    """

    dotted_path: str
    id_field: str
    required_keys: tuple[str, ...] = ()
    optional_keys: tuple[str, ...] = ()

    def allowed_keys(self) -> set[str]:
        return {self.id_field, *self.required_keys, *self.optional_keys}
