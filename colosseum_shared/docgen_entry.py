"""Shared utilities plugin documentation spec."""

from colosseum.docgen_spec import DocgenModuleSpec


def spec() -> DocgenModuleSpec:
    return DocgenModuleSpec(
        module_id="colosseum_shared",
        title="Colosseum Shared",
        import_packages=["colosseum_shared"],
        autodoc_modules=["colosseum_shared"],
        order=30,
        namespace="shared",
    )
