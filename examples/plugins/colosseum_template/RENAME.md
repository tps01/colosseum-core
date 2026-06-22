# Search-and-replace checklist

Use this when forking `colosseum_template` into your own extension. Work top to bottom.

| Find | Replace with | Where |
|------|--------------|-------|
| `colosseum_template` | `your_package` (e.g. `acme_bench`) | Python package directory, imports, docgen `import_packages` |
| `colosseum-template` | `your-distribution` (e.g. `acme-bench`) | `pyproject.toml` `[project].name` |
| `template` | `yournamespace` (e.g. `acme`) | Entry-point keys, `register_namespace`, config section prefix, decorator domain |
| `template.device` | `yournamespace.device` | `ConfigSectionSpec`, bench TOML, validators |
| `Colosseum Template Extension` | Your extension title | `docgen_entry.py`, README |
| `colosseum_template` | `your_module_id` | `DocgenModuleSpec.module_id` |

## Files to edit

1. Rename directory `colosseum_template/` → `your_package/`
2. `pyproject.toml` — `name`, `description`, `dependencies`, entry points, `include` glob
3. `your_package/__init__.py` — namespace string, config section path, optional validator/shutdown
4. `your_package/api.py` — domain in `MeasurementSource`, docstrings
5. `your_package/docgen_entry.py` — `module_id`, `title`, `namespace`, package lists
6. `configs/bench.template.toml` — rename file if desired; update section header `[[yournamespace.device]]`
7. `examples/smoke_test.py` — config path and API calls
8. This README and `RENAME.md` — update or remove template-specific paths

## Do not shadow built-in namespaces

Avoid registering: `equipment`, `shared`, `io`, `host`.
