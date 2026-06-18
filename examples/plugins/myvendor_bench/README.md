# myvendor_bench (example extension)

Reference skeleton for a third-party Colosseum plugin. See `docs/sphinx/source/guides/plugins.rst`.

## Install (editable)

From this directory:

```powershell
pip install -e .
```

## Bench config

```toml
[[myvendor.fixture]]
fixture_id = 1
serial = "DEMO-001"
```

## Smoke test

```python
import colosseum as col

col.config.load_config("path/to/bench.toml")
col.myvendor.measure_widget_count(fixture_id=1, key="widgets")
col.myvendor.verify_widget_count(key="widgets", expected_val=10.0, tolerance=0.0)
col.endex()
```
