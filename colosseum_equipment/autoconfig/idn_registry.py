"""Map instrument *IDN? responses to equipment kind and model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IdnMatch:
    """Classification result for a probed instrument."""

    kind: str
    model: str


@dataclass(frozen=True)
class _PatternRule:
    substring: str
    kind: str
    model: str


# Tier 1: vendor-specific patterns (most specific first).
_TIER1_RULES: tuple[_PatternRule, ...] = (
    _PatternRule("EDU34450A", "dmm", "keysight-edu34450a"),
    _PatternRule("34450A", "dmm", "keysight-edu34450a"),
    _PatternRule("GENESYS", "psu", "tdk-genesys"),
    _PatternRule("TDK-LAMBDA", "psu", "tdk-genesys"),
    _PatternRule("E4438C", "vsg", "keysight-esg"),
    _PatternRule("E4428C", "vsg", "keysight-esg"),
    _PatternRule("E4407B", "speca", "keysight-e4407b"),
    _PatternRule("RSA5100", "rtsa", "tektronix-rsa5100b"),
    _PatternRule("RSA5106B", "rtsa", "tektronix-rsa5100b"),
    _PatternRule("U2001A", "pwrmeter", "keysight-u2001a"),
    _PatternRule("U2000A", "pwrmeter", "keysight-u2000a"),
    _PatternRule("U2000", "pwrmeter", "keysight-u2000"),
    _PatternRule("53220A", "freqcounter", "keysight-53220a"),
    _PatternRule("53230A", "freqcounter", "keysight-53230a"),
    _PatternRule("FCA3000", "freqcounter", "tektronix-fca3000"),
    _PatternRule("FCA3100", "freqcounter", "tektronix-fca3100"),
    _PatternRule("MCA3000", "freqcounter", "tektronix-mca3000"),
    _PatternRule("IT8600", "eload", "itech-it8600"),
    _PatternRule("IT851", "eload", "itech-it8600"),
    _PatternRule("8600", "eload", "chroma-8600"),
    _PatternRule("6050", "eload", "agilent-6050"),
    _PatternRule("MDO4", "oscope", "tektronix-mdo4000"),
    _PatternRule("T3DSO", "oscope", "tektronix-t3dso2000"),
    _PatternRule("TTR500", "vna", "tektronix-ttr500"),
    _PatternRule(",ZNB", "vna", "rohde-znb"),
    _PatternRule("ZNB", "vna", "rohde-znb"),
    _PatternRule("541XX", "vna", "anritsu-541xx"),
    _PatternRule("54110", "vna", "anritsu-541xx"),
    _PatternRule("ADAURA", "attn", "adaura-r3"),
    _PatternRule("R3 ATT", "attn", "adaura-r3"),
)

# Tier 2: conservative keyword heuristics (generic model only).
_TIER2_RULES: tuple[_PatternRule, ...] = (
    _PatternRule("MULTIMETER", "dmm", "generic"),
    _PatternRule("DMM", "dmm", "generic"),
    _PatternRule("POWER SUPPLY", "psu", "generic"),
    _PatternRule("E363", "psu", "generic"),
    _PatternRule("DP832", "psu", "generic"),
    _PatternRule("SIGNAL GENERATOR", "vsg", "generic"),
    _PatternRule("N5182", "vsg", "generic"),
    _PatternRule("N5172", "vsg", "generic"),
    _PatternRule("SPECTRUM ANALYZER", "speca", "generic"),
    _PatternRule(",ESA", "speca", "generic"),
    _PatternRule("E440", "speca", "generic"),
    _PatternRule("REAL-TIME", "rtsa", "generic"),
    _PatternRule("RTSA", "rtsa", "generic"),
    _PatternRule("NETWORK ANALYZER", "vna", "generic"),
    _PatternRule("VNA", "vna", "generic"),
    _PatternRule("OSCILLOSCOPE", "oscope", "generic"),
    _PatternRule("DSO", "oscope", "generic"),
    _PatternRule("ELECTRONIC LOAD", "eload", "generic"),
    _PatternRule("E-LOAD", "eload", "generic"),
    _PatternRule("FREQ COUNTER", "freqcounter", "generic"),
    _PatternRule("FREQUENCY COUNTER", "freqcounter", "generic"),
    _PatternRule("POWER METER", "pwrmeter", "generic"),
    _PatternRule("ATTENUATOR", "attn", "generic"),
    _PatternRule("RF SWITCH", "rfswitch", "generic"),
    _PatternRule("ARBITRARY", "asg", "generic"),
    _PatternRule("SMU", "psu", "generic"),
)


def classify_idn(idn: str) -> IdnMatch | None:
    """Classify a raw *IDN? response into equipment kind and model."""
    normalized = idn.strip().upper()
    if not normalized:
        return None
    for rule in _TIER1_RULES:
        if rule.substring.upper() in normalized:
            return IdnMatch(kind=rule.kind, model=rule.model)
    for rule in _TIER2_RULES:
        if rule.substring.upper() in normalized:
            return IdnMatch(kind=rule.kind, model=rule.model)
    return None


KIND_SECTIONS: dict[str, tuple[str, str]] = {
    "psu": ("equipment.psu", "psu_id"),
    "dmm": ("equipment.dmm", "dmm_id"),
    "vsg": ("equipment.vsg", "vsg_id"),
    "asg": ("equipment.asg", "asg_id"),
    "speca": ("equipment.speca", "speca_id"),
    "rtsa": ("equipment.rtsa", "rtsa_id"),
    "attn": ("equipment.attn", "attn_id"),
    "pwrmeter": ("equipment.pwrmeter", "pwrmeter_id"),
    "rfswitch": ("equipment.rfswitch", "rfswitch_id"),
    "oscope": ("equipment.oscope", "oscope_id"),
    "eload": ("equipment.eload", "eload_id"),
    "freqcounter": ("equipment.freqcounter", "freqcounter_id"),
    "vna": ("equipment.vna", "vna_id"),
}
