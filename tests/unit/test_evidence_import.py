"""Unit tests for importing prior-run evidence."""

from __future__ import annotations

from colosseum.context import init_context
from colosseum.database import CommandRow, MeasurementRow
from colosseum.database.evidence_import import import_evidence_from_previous

from tests.support.helpers import release_context


def test_import_evidence_from_previous(tmp_path, isolated_cwd) -> None:
    source_dir = tmp_path / "prior-pass"
    source_dir.mkdir()
    source_ctx = init_context(test_case_name="prior", no_artifacts=False)
    source_ctx.output_dir = source_dir
    source_ctx.runtime_ready = True
    source_ctx.db.initialize(source_dir / "execution.sqlite")
    source_ctx.db.insert_measurement(
        MeasurementRow(
            domain="core",
            command="measure_value",
            key="stored",
            row_index=2,
            value={"samples": [4.2, None]},
            units="V",
            status="DRY",
            timestamp="2026-01-01T12:00:00+00:00",
        ),
    )
    source_ctx.db.insert_command(
        CommandRow(
            domain="stub",
            command="ping",
            key="k1",
            result={"ok": True},
            status="ERROR",
            optional=True,
            message="unavailable",
            cause="procedural",
            timestamp="2026-01-01T12:00:01+00:00",
        ),
    )
    expected_measurements = source_ctx.db.fetch_all_measurements()
    expected_commands = source_ctx.db.fetch_all_commands()
    source_ctx.db.close()
    source_bytes = (source_dir / "execution.sqlite").read_bytes()

    target_ctx = init_context(test_case_name="rerun", no_artifacts=False)
    try:
        target_ctx.output_dir = isolated_cwd / "outputs" / "2026-01-01_120000_rerun"
        target_ctx.output_dir.mkdir(parents=True)
        target_ctx.db.initialize(target_ctx.output_dir / "execution.sqlite")
        target_ctx.runtime_ready = True

        import_evidence_from_previous(target_ctx, source_dir)

        row = target_ctx.db.get_measurement("core", "measure_value", "stored", row_index=2)
        assert row is not None
        assert row.value == {"samples": [4.2, None]}
        assert target_ctx.db.fetch_all_measurements() == expected_measurements
        assert target_ctx.db.fetch_all_commands() == expected_commands
        assert (source_dir / "execution.sqlite").read_bytes() == source_bytes
        commands = target_ctx.db.fetch_table_rows("commands")
        assert len(commands) == 1
        assert commands[0]["cause"] == "procedural"
        metadata = {item.key: item.value for item in target_ctx.db.fetch_run_metadata()}
        assert metadata["imported_from"] == str(source_dir)
    finally:
        release_context(target_ctx)
