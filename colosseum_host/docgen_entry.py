"""Host plugin documentation spec."""

from colosseum.docgen_spec import DocgenModuleSpec


def spec() -> DocgenModuleSpec:
    return DocgenModuleSpec(
        module_id="colosseum_host",
        title="Colosseum Host",
        import_packages=["colosseum_host"],
        autodoc_modules=["colosseum_host"],
        order=25,
        namespace="host",
    )
