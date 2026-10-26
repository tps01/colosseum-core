"""Optional parameters file loading and kwargs fill."""

from __future__ import annotations

from pathlib import Path

import pytest

from colosseum.config.parameters import (
    ParametersError,
    apply_parameters_to_kwargs,
    attach_parameters,
    coerce_bool,
    is_limit_section,
    load_parameters_file,
    owed_limit_keys,
    resolve_parameters_path,
)
from colosseum.decorators import command, verification
from colosseum.decorators.verification import VerificationResult
from colosseum.exceptions import ProceduralFault


def test_resolve_order_cli_then_entry_then_sibling(tmp_path: Path) -> None:
    script = tmp_path / "dut.py"
    script.write_text("def main():\n    pass\n", encoding="utf-8")
    sibling = tmp_path / "parameters.toml"
    sibling.write_text("[rail]\nexpected_val = 3.3\n", encoding="utf-8")
    entry = tmp_path / "entry.toml"
    entry.write_text("[rail]\nexpected_val = 1.0\n", encoding="utf-8")
    cli = tmp_path / "cli.toml"
    cli.write_text("[rail]\nexpected_val = 5.0\n", encoding="utf-8")

    assert resolve_parameters_path(script_path=script) == sibling.resolve()
    assert resolve_parameters_path(script_path=script, entry_path=entry) == entry.resolve()
    assert (
        resolve_parameters_path(script_path=script, cli_path=cli, entry_path=entry)
        == cli.resolve()
    )
    other = tmp_path / "other"
    other.mkdir()
    assert resolve_parameters_path(script_path=other / "missing.py") is None


def test_load_and_owed_limit_keys(tmp_path: Path) -> None:
    path = tmp_path / "parameters.toml"
    path.write_text(
        """
[rail]
expected_val = 3.3
tolerance = 0.1

[capture]
local_path = "trace.bin"

[floor]
minimum = 0.5
""",
        encoding="utf-8",
    )
    tables = load_parameters_file(path)
    assert tables["rail"]["expected_val"] == 3.3
    assert is_limit_section(tables["rail"]) is True
    assert is_limit_section(tables["capture"]) is False
    assert owed_limit_keys(tables) == ["rail", "floor"]


def test_invalid_parameters_file_is_procedural(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("not = [valid\n", encoding="utf-8")
    with pytest.raises(ParametersError) as excinfo:
        load_parameters_file(path)
    assert isinstance(excinfo.value, ProceduralFault)


def test_apply_fill_file_wins_and_unknown_key(tmp_path: Path) -> None:
    tables = {"rail": {"expected_val": 3.3, "tolerance": 0.1}}
    filled = apply_parameters_to_kwargs(
        {"tolerance": 0.5, "note": "call"},
        key="rail",
        parameters=tables,
    )
    assert filled["expected_val"] == 3.3
    assert filled["tolerance"] == 0.1
    assert filled["note"] == "call"
    assert apply_parameters_to_kwargs({"x": 1}, key="rail", parameters=None) == {"x": 1}
    assert apply_parameters_to_kwargs({"x": 1}, key="missing", parameters=tables) == {"x": 1}


def test_command_key_stripped_and_fill(unit_runtime_context, tmp_path: Path) -> None:
    path = tmp_path / "parameters.toml"
    path.write_text("[step]\nvoltage = 3.3\n", encoding="utf-8")
    attach_parameters(unit_runtime_context, path)

    @command
    def set_rail(*, voltage: float) -> float:
        return voltage

    assert set_rail(key="step") == 3.3
    assert set_rail(key="step", voltage=1.8) == 3.3


def test_command_unknown_key_uses_the_call(unit_runtime_context, tmp_path: Path) -> None:
    path = tmp_path / "parameters.toml"
    path.write_text("[step]\nvoltage = 3.3\n", encoding="utf-8")
    attach_parameters(unit_runtime_context, path)

    @command
    def set_rail(*, voltage: float = 0.0) -> float:
        return voltage

    assert set_rail(key="other", voltage=1.8) == 1.8
    row = unit_runtime_context.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "PASS"
    assert row["key"] == "other"


def test_verification_fills_limits(unit_runtime_context, tmp_path: Path) -> None:
    path = tmp_path / "parameters.toml"
    path.write_text(
        "[widgets]\nexpected_val = 10.0\ntolerance = 0.5\n",
        encoding="utf-8",
    )
    attach_parameters(unit_runtime_context, path)

    @verification
    def check(*, key: str, expected_val: float, tolerance: float = 0.0) -> VerificationResult:
        return VerificationResult(
            status="PASS",
            message=f"{expected_val}:{tolerance}",
            actual=expected_val,
        )

    result = check(key="widgets")
    assert result.status == "PASS"
    assert result.message == "10.0:0.5"


def test_no_parameters_file_passthrough(unit_runtime_context) -> None:
    @command
    def set_rail(*, voltage: float) -> float:
        return voltage

    assert set_rail(voltage=2.5, key="step") == 2.5


def test_error_log_contains_cause_and_redacts_password(unit_runtime_context) -> None:
    from colosseum.logging.setup import setup_logging

    setup_logging(unit_runtime_context, console=False, file=True)

    @command
    def login(*, password: str, key: str = "") -> None:
        raise RuntimeError("auth failed")

    with pytest.raises(RuntimeError, match="auth failed"):
        login(password="super-secret", key="auth")

    assert unit_runtime_context.output_dir is not None
    text = (unit_runtime_context.output_dir / "debug.log").read_text(encoding="utf-8")
    assert "cause=unit" in text
    assert "super-secret" not in text
    assert "***" in text
    row = unit_runtime_context.db.fetch_table_rows("commands")[-1]
    assert row["cause"] == "unit"


def test_coerce_bool_spellings() -> None:
    assert coerce_bool(True) is True
    assert coerce_bool(False) is False
    assert coerce_bool(1) is True
    assert coerce_bool(0) is False
    for spelling in ("True", "true", "T", "t", "yes", "Y", "1"):
        assert coerce_bool(spelling) is True
    for spelling in ("False", "false", "F", "f", "no", "N", "0"):
        assert coerce_bool(spelling) is False
    with pytest.raises(ParametersError, match="optional"):
        coerce_bool("maybe")


def test_file_optional_overrides_call(unit_runtime_context, tmp_path: Path) -> None:
    path = tmp_path / "parameters.toml"
    path.write_text('[probe]\noptional = "T"\n', encoding="utf-8")
    attach_parameters(unit_runtime_context, path)

    @verification
    def check(*, key: str, optional: bool = False) -> bool:
        return False

    result = check(key="probe", optional=False)
    assert result.status == "FAIL"
    assert result.optional is True
    assert unit_runtime_context.result_aggregator.overall_pass() is True


def test_file_optional_false_string_fails_the_run(unit_runtime_context, tmp_path: Path) -> None:
    path = tmp_path / "parameters.toml"
    path.write_text('[probe]\noptional = "false"\n', encoding="utf-8")
    attach_parameters(unit_runtime_context, path)

    @verification
    def check(*, key: str, optional: bool = False) -> bool:
        return False

    result = check(key="probe")
    assert result.status == "FAIL"
    assert result.optional is False
    assert unit_runtime_context.result_aggregator.overall_pass() is False


def test_file_description_overrides_call(unit_runtime_context, tmp_path: Path) -> None:
    path = tmp_path / "parameters.toml"
    path.write_text(
        '[probe]\ndescription = "from file"\nexpected_val = 1.0\n',
        encoding="utf-8",
    )
    attach_parameters(unit_runtime_context, path)

    @verification
    def check(*, key: str, expected_val: float, description: str = "") -> VerificationResult:
        return VerificationResult(status="PASS", message=description, actual=expected_val)

    result = check(key="probe", expected_val=9.0, description="from call")
    assert result.message == "from file"
    assert result.actual == 1.0


def test_procedural_fault_sets_cause(unit_runtime_context) -> None:
    @command
    def open_bench(*, key: str = "") -> None:
        raise ProceduralFault("session never opened")

    with pytest.raises(ProceduralFault):
        open_bench(key="bench")
    row = unit_runtime_context.db.fetch_table_rows("commands")[-1]
    assert row["status"] == "ERROR"
    assert row["cause"] == "procedural"
    assert unit_runtime_context.result_aggregator.has_required_procedural_command_error()
