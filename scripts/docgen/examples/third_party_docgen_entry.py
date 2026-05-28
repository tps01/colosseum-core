"""
Example ``colosseum.docgen`` entry point for a third-party extension.

Copy this pattern into ``myvendor_bench/docgen_entry.py`` and register::

    [project.entry-points."colosseum.docgen"]
    myvendor = "myvendor_bench.docgen_entry:spec"
"""

from colosseum.docgen_spec import DocgenModuleSpec


def spec() -> DocgenModuleSpec:
    return DocgenModuleSpec(
        module_id="myvendor_bench",
        title="My Vendor Bench",
        import_packages=["myvendor_bench"],
        autodoc_modules=["myvendor_bench"],
        order=50,
        namespace="myvendor",
    )
