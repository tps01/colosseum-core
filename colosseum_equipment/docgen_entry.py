"""Equipment plugin documentation spec."""

from colosseum.docgen_spec import DocgenModuleSpec


def spec() -> DocgenModuleSpec:
    return DocgenModuleSpec(
        module_id="colosseum_equipment",
        title="Colosseum Equipment",
        import_packages=["colosseum_equipment"],
        autodoc_modules=["colosseum_equipment"],
        order=20,
        namespace="equipment",
    )
