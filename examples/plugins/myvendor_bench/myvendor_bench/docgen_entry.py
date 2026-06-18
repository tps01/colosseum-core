from colosseum.docgen_spec import DocgenModuleSpec


def spec() -> DocgenModuleSpec:
    return DocgenModuleSpec(
        module_id="myvendor_bench",
        title="My Vendor Bench (example)",
        import_packages=["myvendor_bench"],
        autodoc_modules=["myvendor_bench"],
        order=50,
        namespace="myvendor",
    )
