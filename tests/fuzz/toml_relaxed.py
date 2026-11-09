"""Atheris target for relaxed TOML, independent of all Colosseum plugins."""

from __future__ import annotations

import json
import sys


def check_input(data: bytes) -> None:
    from colosseum.config.toml_relaxed import loads_relaxed, prepare_toml_text, tomllib

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    prepared = prepare_toml_text(text)
    assert prepare_toml_text(prepared) == prepared
    try:
        parsed = loads_relaxed(text)
    except (tomllib.TOMLDecodeError, RecursionError):
        pass
    else:
        assert isinstance(parsed, dict)

    # JSON basic-string escapes are supported by TOML. Generate known-valid
    # strings instead of assuming all valid TOML is unchanged by relaxation.
    quoted = json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007f")
    document = f"value = {quoted} # outside comment\nnumber = 42\nflag = true\n"
    expected = {"value": text, "number": 42, "flag": True}
    assert tomllib.loads(document) == expected
    assert loads_relaxed(document) == expected

    # A prefix keeps the generated bare word unambiguously nonnumeric/nonboolean.
    word = "value_" + data[:64].hex()
    assert loads_relaxed(f"value = {word} # comment\n") == {"value": word}
    token = ("yes", "True", "F", "no")[len(data) % 4]
    assert loads_relaxed(f"flag = {token}\n") == {"flag": token in ("yes", "True")}
    body = "key = pending\nflag = yes\n# literal comment\n" + word
    multiline = 'value = """\n' + body + '\n"""\n'
    assert loads_relaxed(multiline) == tomllib.loads(multiline)
    check_string_layouts(data)
    check_structured_values(data)
    check_section_normalization(data)


def check_string_layouts(data: bytes) -> None:
    """Preserve literal/basic multiline bodies and recover after closing quotes."""
    from colosseum.config.toml_relaxed import loads_relaxed, tomllib

    word = "value_" + data[:64].hex()
    body = f"key = {word}\nflag = yes\n# literal comment\n"
    for quote in (chr(34), chr(39)):
        for extra in range(3):
            document = "value = " + quote * 3 + "\n" + body + quote * (3 + extra)
            expected = tomllib.loads(document)
            expected["flag"] = True
            for newline in ("\n", "\r\n"):
                relaxed = (document + " # closing comment\nflag = yes\n").replace("\n", newline)
                assert loads_relaxed(relaxed) == expected
    continued = 'value = """\n' + word + "\\\n  \t" + word + '\n"""\n'
    assert loads_relaxed(continued) == tomllib.loads(continued)


def check_structured_values(data: bytes) -> None:
    """Check nested containers and typed numeric values against standard TOML."""
    from colosseum.config.toml_relaxed import loads_relaxed, tomllib

    number = int.from_bytes(data[:8], "big", signed=True)
    label = json.dumps("label_" + data[:32].hex())
    document = (
        f"number = {number}\nhex = 0x{abs(number):x}\noctal = 0o{abs(number):o}\n"
        "fraction = -1_024.25e-2\npositive = +42\n"
        "infinity = inf\nnegative_infinity = -inf\nnot_a_number = nan\n"
        f"items = [\n{label}, # array comment\n[true, false, {number}],\n]\n"
        f'options = {{ "quoted.key" = {label}, count = {number}, enabled = true }}\n'
    )
    # JSON serialization makes NaN comparable while distinguishing numbers
    # from strings, booleans from integers, and preserving nested structure.
    expected = tomllib.loads(document)
    actual = json.dumps(loads_relaxed(document), sort_keys=True)
    assert actual == json.dumps(expected, sort_keys=True)


def check_section_normalization(data: bytes) -> None:
    """Exercise parse -> normalize -> lookup with a local, unregistered spec."""
    from colosseum.config.loader import ConfigError, ConfigStore, normalize_sections
    from colosseum.config.sections import ConfigSectionSpec
    from colosseum.config.toml_relaxed import loads_relaxed

    spec = ConfigSectionSpec("fuzz.device", "device_id", required_keys=("label",))
    base = int.from_bytes(data[:4], "big", signed=True)
    count = 1 + (data[0] % 4 if data else 0)
    label = "device_" + data[:16].hex()
    document = "".join(
        f"[[fuzz.device]]\ndevice_id = {base + index}\nlabel = {label}\n" for index in range(count)
    )
    raw = loads_relaxed(document)
    before = json.dumps(raw, sort_keys=True)
    normalized = normalize_sections(raw, [spec])
    expected = {base + index: {"device_id": base + index, "label": label} for index in range(count)}
    assert normalized == {spec.dotted_path: expected}
    assert json.dumps(raw, sort_keys=True) == before
    reversed_raw = {"fuzz": {"device": list(reversed(raw["fuzz"]["device"]))}}
    assert normalize_sections(reversed_raw, [spec]) == normalized
    store = ConfigStore(raw, normalized, {spec.dotted_path: spec})
    assert store.list_items(spec.dotted_path) == list(expected.values())
    assert store.require_item(spec.dotted_path, base) == expected[base]
    single = {"fuzz": {"device": expected[base]}}
    assert normalize_sections(single, [spec]) == {spec.dotted_path: {base: expected[base]}}

    invalid_id = (True, False, None, "1", 1.5)[len(data) % 5]
    for rows in (
        [{"device_id": invalid_id}],
        [expected[base], expected[base]],
        [None],
    ):
        invalid = {"fuzz": {"device": rows}}
        snapshot = json.dumps(invalid, sort_keys=True)
        try:
            normalize_sections(invalid, [spec])
        except ValueError:
            pass
        else:
            raise AssertionError(f"Accepted invalid section: {rows!r}")
        assert json.dumps(invalid, sort_keys=True) == snapshot

    missing = {"fuzz": {"device": {"device_id": base}}}
    missing_store = ConfigStore(
        missing, normalize_sections(missing, [spec]), {spec.dotted_path: spec},
    )
    for current, item_id in ((store, base + count), (missing_store, base)):
        try:
            current.require_item(spec.dotted_path, item_id)
        except ConfigError:
            pass
        else:
            raise AssertionError("Missing ID/required field did not raise ConfigError")


def main() -> None:
    """Instrument core imports and forward libFuzzer arguments unchanged."""
    import atheris

    with atheris.instrument_imports():
        import colosseum.config.toml_relaxed  # noqa: F401
    atheris.Setup(sys.argv, atheris.instrument_func(check_input))
    atheris.Fuzz()


if __name__ == "__main__":
    main()
