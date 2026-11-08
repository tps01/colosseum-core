"""Integration-tier pytest fixtures."""

# Integration tests use disk execution.sqlite under isolated_cwd/outputs/.
# COLOSSEUM_DEFER_DB_COMMITS (autouse in common_fixtures) batches commits until
# endex/close; subprocess e2e clears the env var so CLI runs commit per insert.
