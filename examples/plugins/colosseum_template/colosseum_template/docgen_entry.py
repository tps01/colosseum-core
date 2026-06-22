from colosseum.docgen_spec import DocgenModuleSpec


def spec() -> DocgenModuleSpec:
    # TODO: Update module_id, title, order, and namespace when forking.
    return DocgenModuleSpec(
        module_id="colosseum_template",
        title="Colosseum Template Extension",
        import_packages=["colosseum_template"],
        autodoc_modules=["colosseum_template"],
        order=50,
        namespace="template",
    )
