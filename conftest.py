"""Top-level fixture discovery. Tier conftests must not redeclare pytest_plugins."""

pytest_plugins = ["tests.support.common_fixtures"]
