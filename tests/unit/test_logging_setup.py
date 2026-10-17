"""Logging setup: file + console handlers."""

from __future__ import annotations

import logging

from colosseum.logging.setup import attach_console_logger, setup_logging


def test_setup_logging_console_info_filters_debug(unit_runtime_context, capsys) -> None:
    logger = setup_logging(
        unit_runtime_context,
        console=True,
        console_level=logging.INFO,
    )
    logger.debug("hidden debug")
    logger.info("visible info")

    out = capsys.readouterr().out
    assert "visible info" in out
    assert "hidden debug" not in out


def test_attach_console_logger_skips_identity_header(unit_runtime_context, capsys) -> None:
    """After a slot finishes, console reattach must not reprint the identity block."""
    setup_logging(unit_runtime_context, console=True, file=True)
    attach_console_logger(unit_runtime_context)
    logger = logging.getLogger("colosseum")
    logger.info("Slot result: PASS (exit 0)")

    out = capsys.readouterr().out
    assert out.count("Colosseum version:") == 1
    assert out.count("Python version:") == 1
    assert "Slot result: PASS (exit 0)" in out
    assert unit_runtime_context.output_dir is not None
    log_text = (unit_runtime_context.output_dir / "debug.log").read_text(encoding="utf-8")
    assert log_text.count("Colosseum version:") == 1
    assert "Slot result: PASS (exit 0)" not in log_text


def test_session_reattach_after_finalize_skips_header(
    unit_runtime_context, capsys, tmp_path,
) -> None:
    """finalize_script_slot reattach must not emit a second identity header."""
    from colosseum.runner.runtime import begin_script_slot, ensure_suite_runtime_ready

    ctx = unit_runtime_context
    ctx.session.kind = "suite"
    ctx.suite_name = "header_suite"
    ctx.no_artifacts = False
    ensure_suite_runtime_ready(ctx, "header_suite")
    begin_script_slot(ctx, "slot_a", phase="test", affects_suite_result=True)
    ctx.slot_script_path = tmp_path / "slot_a.py"
    ctx.slot_script_path.write_text("def main():\n    pass\n", encoding="utf-8")

    from colosseum.runner.runtime import finalize_script_slot

    capsys.readouterr()  # clear start/slot headers already emitted
    finalize_script_slot(ctx, script_path=ctx.slot_script_path)
    out = capsys.readouterr().out
    assert "Colosseum version:" not in out
    assert ctx.logger is not None
    ctx.logger.info("post-finalize message")
    assert "post-finalize message" in capsys.readouterr().out


def test_suite_header_uses_suite_container_path(unit_runtime_context, capsys, tmp_path) -> None:
    """Suite start should report the suite container, not a fake no-artifacts line."""
    container = tmp_path / "suite_container"
    container.mkdir()
    unit_runtime_context.output_dir = None
    unit_runtime_context.suite_output_dir = container
    unit_runtime_context.no_artifacts = False
    unit_runtime_context.test_case_name = "fixture_happy"
    unit_runtime_context.suite_name = "fixture_happy"
    unit_runtime_context.session.kind = "suite"

    setup_logging(unit_runtime_context, console=True, file=False)

    out = capsys.readouterr().out
    assert f"Output directory: {container}" in out
    assert "no-artifacts mode" not in out


def test_suite_kind_without_paths_is_not_fake_no_artifacts(unit_runtime_context, capsys) -> None:
    """session.kind=suite with cleared paths must not print a fake no-artifacts line."""
    unit_runtime_context.output_dir = None
    unit_runtime_context.suite_output_dir = None
    unit_runtime_context.no_artifacts = False
    unit_runtime_context.session.kind = "suite"

    setup_logging(unit_runtime_context, console=True, file=False)

    out = capsys.readouterr().out
    assert "no-artifacts mode" not in out
    assert "suite" in out.lower()


def test_setup_logging_console_debug_shows_debug(unit_runtime_context, capsys) -> None:
    logger = setup_logging(
        unit_runtime_context,
        console=True,
        console_level=logging.DEBUG,
    )
    logger.debug("visible debug")

    out = capsys.readouterr().out
    assert "visible debug" in out
