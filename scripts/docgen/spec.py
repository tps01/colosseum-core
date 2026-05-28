"""Re-export public docgen contract for scripts running from the repository."""

from colosseum.docgen_spec import DOCGEN_ENTRY_GROUP, DocgenModuleSpec

__all__ = ["DOCGEN_ENTRY_GROUP", "DocgenModuleSpec"]
