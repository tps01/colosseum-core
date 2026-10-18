"""Artifact paths stay usable after run rename and evidence import."""

from __future__ import annotations

from pathlib import Path

from colosseum.context import init_context
from colosseum.database import MeasurementRow
from colosseum.database.artifact_paths import stored_artifact_path
from colosseum.database.evidence_import import import_evidence_from_previous
from colosseum.runner.runtime import rename_run_directory_for_result


def test_relative_artifact_survives_pass_rename(tmp_path: Path) -> None:
    run_dir = tmp_path / "2026-10-18_120000_mask"
    run_dir.mkdir()
    csv_path = run_dir / "speca" / "trace.csv"
    csv_path.parent.mkdir()
    csv_path.write_text("frequency_hz,amplitude_dbm\n1,2\n", encoding="utf-8")

    ctx = init_context(test_case_name="mask", no_artifacts=False)
    ctx.output_dir = run_dir
    ctx.runtime_ready = True
    ctx.db.initialize(run_dir / "execution.sqlite")
    ctx.db.insert_measurement(
        MeasurementRow(
            domain="equipment",
            command="save_trace_data",
            key="speca_trace_1",
            value={"points": 1},
            artifact_path=stored_artifact_path(csv_path, run_dir),
        ),
    )
    saved = ctx.db.get_measurement("equipment", "save_trace_data", "speca_trace_1")
    assert saved is not None
    assert saved.artifact_path == "speca/trace.csv"
    ctx.db.close()

    renamed = rename_run_directory_for_result(run_dir, "PASS")
    inspect = init_context(test_case_name="inspect", no_artifacts=False)
    inspect.db.open_readonly(renamed / "execution.sqlite")
    row = inspect.db.get_measurement("equipment", "save_trace_data", "speca_trace_1")
    assert row is not None
    resolved = inspect.db.resolve_artifact_path(row.artifact_path)
    assert resolved is not None
    assert resolved.is_file()
    assert resolved == (renamed / "speca" / "trace.csv").resolve()
    inspect.db.close()


def test_legacy_absolute_artifact_rebases_after_rename(tmp_path: Path) -> None:
    run_dir = tmp_path / "2026-10-18_120000_scope"
    run_dir.mkdir()
    csv_path = run_dir / "oscope" / "wave.csv"
    csv_path.parent.mkdir()
    csv_path.write_text("time_s,voltage_v\n0,1\n", encoding="utf-8")
    stale = str(csv_path)

    ctx = init_context(test_case_name="scope", no_artifacts=False)
    ctx.db.initialize(run_dir / "execution.sqlite")
    ctx.db.insert_measurement(
        MeasurementRow(
            domain="equipment",
            command="save_waveform",
            key="wave",
            artifact_path=stale,
        ),
    )
    ctx.db.close()

    renamed = rename_run_directory_for_result(run_dir, "FAIL")
    assert not Path(stale).is_file()
    inspect = init_context(test_case_name="inspect", no_artifacts=False)
    inspect.db.open_readonly(renamed / "execution.sqlite")
    row = inspect.db.get_measurement("equipment", "save_waveform", "wave")
    assert row is not None
    resolved = inspect.db.resolve_artifact_path(row.artifact_path)
    assert resolved is not None and resolved.is_file()
    assert resolved.parent.name == "oscope"
    inspect.db.close()


def test_imported_artifact_resolves_against_previous_run(
    tmp_path: Path,
    isolated_cwd: Path,
) -> None:
    source_dir = tmp_path / "prior-pass"
    (source_dir / "speca").mkdir(parents=True)
    csv_path = source_dir / "speca" / "trace.csv"
    csv_path.write_text("frequency_hz,amplitude_dbm\n1,-40\n", encoding="utf-8")

    source = init_context(test_case_name="prior", no_artifacts=False)
    source.output_dir = source_dir
    source.runtime_ready = True
    source.db.initialize(source_dir / "execution.sqlite")
    source.db.insert_measurement(
        MeasurementRow(
            domain="equipment",
            command="save_trace_data",
            key="trace",
            artifact_path=str(csv_path),
        ),
    )
    source.db.close()

    target_dir = isolated_cwd / "outputs" / "2026-01-01_120000_replay"
    target_dir.mkdir(parents=True)
    target = init_context(test_case_name="replay", no_artifacts=False)
    target.output_dir = target_dir
    target.runtime_ready = True
    target.db.initialize(target_dir / "execution.sqlite")
    import_evidence_from_previous(target, source_dir)

    row = target.db.get_measurement("equipment", "save_trace_data", "trace")
    assert row is not None
    assert row.artifact_path == "speca/trace.csv"
    resolved = target.db.resolve_artifact_path(row.artifact_path)
    assert resolved is not None
    assert resolved.is_file()
    assert resolved == csv_path.resolve()
    target.db.close()
