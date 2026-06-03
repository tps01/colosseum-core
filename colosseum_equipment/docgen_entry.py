"""Equipment plugin documentation spec."""

from pathlib import Path

from colosseum.docgen_spec import DocgenModuleSpec


def spec() -> DocgenModuleSpec:
    return DocgenModuleSpec(
        module_id="colosseum_equipment",
        title="Colosseum Equipment",
        import_packages=["colosseum_equipment", "colosseum_equipment.io"],
        autodoc_modules=["colosseum_equipment", "colosseum_equipment.io"],
        order=20,
        namespace="equipment",
    )
