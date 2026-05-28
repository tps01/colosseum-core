"""Summary artifact content (Wave 3)."""

from __future__ import annotations

from colosseum.decorators.verification import VerificationResult
from colosseum.summary.writer import SummaryWriter


def test_summary_lists_failed_required(unit_runtime_context) -> None:
    ctx = unit_runtime_context
    out = ctx.output_dir
    assert out is not None
    ctx.result_aggregator.record_verification(
        VerificationResult(status="FAIL", message="out of tolerance", optional=False),
        key="rail_a",
        command="verify_voltage",
        domain="equipment",
    )
    SummaryWriter().write(out, ctx.result_aggregator, ctx)
    text = (out / "summary.txt").read_text(encoding="utf-8")
    assert "Overall result: FAIL" in text
    assert "rail_a" in text
    assert "Exit code: 1" in text
    import json

    payload = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert payload["overall_result"] == "FAIL"
    assert payload["exit_code"] == 1
    assert payload["failed_required_verifications"][0]["key"] == "rail_a"
