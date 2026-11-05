"""Analysis hook: bundle every colosseum plugin installed in the build env.

PyInstaller only traces static imports. Plugin registration goes through
importlib.metadata entry points, and several plugins then import more modules
by string (lazy_module) or by pkgutil.iter_modules (instrument packages).
Those names have to be listed here or they are absent from the exe.
"""

from __future__ import annotations

from importlib.metadata import entry_points

try:
    from importlib.metadata import packages_distributions
except ImportError:  # Python 3.9
    packages_distributions = None  # type: ignore[assignment,misc]

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)


def _plugin_entry_points():
    discovered = entry_points()
    select = getattr(discovered, "select", None)
    if select is not None:
        return list(select(group="colosseum.plugins"))
    return list(discovered.get("colosseum.plugins", []))


def _dist_name(entry_point):
    dist = getattr(entry_point, "dist", None)
    if dist is not None and getattr(dist, "name", None):
        return dist.name
    if packages_distributions is None:
        return None
    top_level = entry_point.value.split(":", 1)[0].split(".", 1)[0]
    names = packages_distributions().get(top_level, [])
    return names[0] if names else None


hiddenimports = []
datas = []
binaries = []

# colosseum/__init__.py calls metadata.version("colosseum-core") on import.
datas += copy_metadata("colosseum-core")
datas += collect_data_files("colosseum")  # gui/assets next to colosseum.gui

seen_dists = set()
for entry_point in _plugin_entry_points():
    module_name = entry_point.value.split(":", 1)[0].strip()
    package_name = module_name.split(".", 1)[0]
    # Whole package, not just the register module. This is what puts
    # colosseum_equipment.instruments.* into the archive so
    # pkgutil.iter_modules can see them, and what pulls in lazy targets
    # such as colosseum_messaging.api.
    print(f"hook-colosseum: collecting {entry_point.name} -> {package_name}")
    hiddenimports += collect_submodules(package_name)
    datas += collect_data_files(package_name)
    binaries += collect_dynamic_libs(package_name)

    dist_name = _dist_name(entry_point)
    if dist_name and dist_name not in seen_dists:
        seen_dists.add(dist_name)
        # entry_points.txt plus METADATA. Without this, entry_points()
        # inside the exe returns an empty colosseum.plugins group.
        datas += copy_metadata(dist_name)
