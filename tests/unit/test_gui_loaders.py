from __future__ import annotations

import json

from colosseum.gui.loaders import load_detail_snapshot, load_run_browser_snapshot


def test_load_run_browser_snapshot_reads_statuses(isolated_cwd) -> None:
    pass_run = isolated_cwd / "outputs" / "2026-01-01_120000_pass-pass"
    incomplete_run = isolated_cwd / "playground" / "outputs" / "2026-01-01_120001_incomplete"
    pass_run.mkdir(parents=True)
    incomplete_run.mkdir(parents=True)
    (pass_run / "summary.json").write_text(
        json.dumps({"overall_result": "PASS"}),
        encoding="utf-8",
    )

    snapshot = load_run_browser_snapshot(isolated_cwd)

    statuses = {row.entry.path.name: row.status for row in snapshot.rows}
    assert statuses[pass_run.name] == "PASS"
    assert statuses[incomplete_run.name] == "incomplete"
    assert snapshot.output_dirs == {pass_run.parent, incomplete_run.parent}


def test_load_detail_snapshot_reports_missing_artifacts(isolated_cwd) -> None:
    run_dir = isolated_cwd / "outputs" / "2026-01-01_120000_empty"
    run_dir.mkdir(parents=True)

    snapshot = load_detail_snapshot(run_dir, table="measurements")

    assert snapshot.run_dir == run_dir
    assert snapshot.log_error == f"No debug.log in {run_dir.name}."
    assert snapshot.summary is None
    assert snapshot.table_error == f"No execution.sqlite in {run_dir.name}."
    assert snapshot.verifications_error == "No execution.sqlite."
