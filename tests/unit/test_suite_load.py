"""U-SUITE-01: suite TOML loading."""

from __future__ import annotations

from datetime import timedelta

import pytest

from colosseum.runner.suite import (
    SuiteError,
    load_suite_toml,
    parse_repeat_duration,
)


def test_load_happy_suite(fixtures_dir) -> None:
    suite = load_suite_toml(fixtures_dir / "suites" / "happy.toml")
    assert suite.name == "fixture_happy"
    assert len(suite.tests) == 1
    assert suite.tests[0].path.name == "pass_test.py"
    assert suite.tests[0].repeat_count == 1
    assert suite.tests[0].repeat_for is None
    assert suite.between_tests == []
    assert suite.setup[0].name == "setup_ok.py"
    assert suite.fail_fast is False
    assert suite.cycle_count == 1
    assert suite.cycle_for is None


def test_missing_name_raises(tmp_path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text('tests = ["../scripts/pass_test.py"]\n', encoding="utf-8")
    with pytest.raises(SuiteError, match="requires string field `name`"):
        load_suite_toml(path)


def test_empty_tests_raises(tmp_path) -> None:
    path = tmp_path / "empty.toml"
    path.write_text('name = "x"\ntests = []\n', encoding="utf-8")
    with pytest.raises(SuiteError, match="non-empty `tests`"):
        load_suite_toml(path)


def test_paths_resolve_relative_to_suite_file(fixtures_dir) -> None:
    suite = load_suite_toml(fixtures_dir / "suites" / "happy.toml")
    assert suite.tests[0].path.is_file()
    assert "fixtures" in str(suite.tests[0].path)


def test_fail_fast_true_loads(fixtures_dir) -> None:
    suite = load_suite_toml(fixtures_dir / "suites" / "multi_test_fail_fast_crash.toml")
    assert suite.fail_fast is True
    assert len(suite.tests) == 2


def test_fail_fast_accepts_bool_spellings(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "fail_fast_t.toml"
    path.write_text(
        f'name = "x"\nfail_fast = T\ntests = ["{script.as_posix()}"]\n',
        encoding="utf-8",
    )
    assert load_suite_toml(path).fail_fast is True
    path.write_text(
        f'name = "x"\nfail_fast = "no"\ntests = ["{script.as_posix()}"]\n',
        encoding="utf-8",
    )
    assert load_suite_toml(path).fail_fast is False


def test_fail_fast_non_bool_raises(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "bad_fail_fast.toml"
    path.write_text(
        f'name = "x"\nfail_fast = "maybe"\ntests = ["{script.as_posix()}"]\n',
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match="fail_fast.*boolean"):
        load_suite_toml(path)


def test_load_between_tests(fixtures_dir) -> None:
    suite = load_suite_toml(fixtures_dir / "suites" / "between_two_tests.toml")
    assert len(suite.between_tests) == 1
    assert suite.between_tests[0].name == "count_between.py"


def test_load_repeat_count_table(fixtures_dir) -> None:
    suite = load_suite_toml(fixtures_dir / "suites" / "repeat_count.toml")
    assert len(suite.tests) == 1
    assert suite.tests[0].repeat_count == 3
    assert suite.tests[0].repeat_for is None


def test_load_repeat_for_table(fixtures_dir) -> None:
    suite = load_suite_toml(fixtures_dir / "suites" / "repeat_for.toml")
    assert suite.tests[0].repeat_for == timedelta(seconds=1)


def test_load_repeat_for_table(fixtures_dir) -> None:
    suite = load_suite_toml(fixtures_dir / "suites" / "repeat_for.toml")
    assert suite.tests[0].repeat_for == timedelta(seconds=1)


def test_load_per_entry_parameters(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    low = tmp_path / "low.toml"
    high = tmp_path / "high.toml"
    low.write_text("[rail]\nexpected_val = 1.0\n", encoding="utf-8")
    high.write_text("[rail]\nexpected_val = 5.0\n", encoding="utf-8")
    path = tmp_path / "params_suite.toml"
    path.write_text(
        "\n".join(
            [
                'name = "params_demo"',
                "tests = [",
                f'  {{ path = "{script.as_posix()}", parameters = "{low.name}" }},',
                f'  {{ path = "{script.as_posix()}", parameters = "{high.name}" }},',
                "]",
                "",
            ],
        ),
        encoding="utf-8",
    )
    suite = load_suite_toml(path)
    assert len(suite.tests) == 2
    assert suite.tests[0].path == suite.tests[1].path
    assert suite.tests[0].parameters == low.resolve()
    assert suite.tests[1].parameters == high.resolve()


def test_load_fail_fast_setup_fixture(fixtures_dir) -> None:
    suite = load_suite_toml(fixtures_dir / "suites" / "setup_fail_fail_fast.toml")
    assert suite.fail_fast is True


def test_rip_cord_key_rejected(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "bad_rip_cord.toml"
    path.write_text(
        f'name = "x"\nrip_cord = true\ntests = ["{script.as_posix()}"]\n',
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match="rip_cord.*removed.*fail_fast"):
        load_suite_toml(path)


def test_repeat_count_and_repeat_for_rejected(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "both.toml"
    path.write_text(
        f'name = "x"\ntests = [{{ path = "{script.as_posix()}", repeat_count = 2, repeat_for = "1s" }}]\n',
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match="cannot set both repeat_count and repeat_for"):
        load_suite_toml(path)


def test_repeat_count_zero_rejected(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "zero.toml"
    path.write_text(
        f'name = "x"\ntests = [{{ path = "{script.as_posix()}", repeat_count = 0 }}]\n',
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match="repeat_count must be >= 1"):
        load_suite_toml(path)


def test_invalid_repeat_for_duration(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "bad_duration.toml"
    path.write_text(
        f'name = "x"\ntests = [{{ path = "{script.as_posix()}", repeat_for = "bad" }}]\n',
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match="Invalid repeat_for duration"):
        load_suite_toml(path)


@pytest.mark.parametrize(
    ("value", "expected_seconds"),
    [
        ("30s", 30),
        ("90m", 90 * 60),
        ("24h", 24 * 3600),
        ("1d", 86400),
        ("1d12h", 86400 + 12 * 3600),
    ],
)
def test_parse_repeat_duration(value: str, expected_seconds: int) -> None:
    assert parse_repeat_duration(value).total_seconds() == expected_seconds


def test_cycle_count_and_cycle_for_rejected(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "both_cycle.toml"
    path.write_text(
        f'name = "x"\ncycle_count = 2\ncycle_for = "1s"\ntests = ["{script.as_posix()}"]\n',
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match="cannot set both cycle_count and cycle_for"):
        load_suite_toml(path)


def test_cycle_count_zero_rejected(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "zero_cycle.toml"
    path.write_text(
        f'name = "x"\ncycle_count = 0\ntests = ["{script.as_posix()}"]\n',
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match=r"cycle_count` must be >= 1"):
        load_suite_toml(path)


def test_invalid_cycle_for_duration(tmp_path, fixtures_dir) -> None:
    script = fixtures_dir / "scripts" / "pass_test.py"
    path = tmp_path / "bad_cycle.toml"
    path.write_text(
        f'name = "x"\ncycle_for = "bad"\ntests = ["{script.as_posix()}"]\n',
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match="Invalid cycle_for duration"):
        load_suite_toml(path)

