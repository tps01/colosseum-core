"""User-facing `col.shared` namespace."""

from colosseum_shared.parsing import text as parsing
from colosseum_shared.regex import api as regex
from colosseum_shared.ssh import api as ssh

__all__ = ["ssh", "regex", "parsing"]
