"""Colosseum core documentation module spec (``colosseum.docgen`` entry point)."""

from colosseum.docgen_spec import DocgenModuleSpec


def spec() -> DocgenModuleSpec:
    return DocgenModuleSpec(
        module_id="colosseum",
        title="Colosseum Core",
        import_packages=["colosseum"],
        autodoc_modules=["colosseum"],
        order=10,
        namespace=None,
    )
