# DDD: Equipment VSG and SpecA

> **Archived planning document.** For current behavior see [scope.md](../../../scope.md), Sphinx user guides, examples, and the codebase. Wave references below are historical only.


## Responsibilities

High-level RF bench APIs for vector/signal generators and spectrum analyzers (including Tektronix RTSA), with generic SCPI drivers and vendor reference implementations per [ADR-006](../decisions/adr-006-vendor-instruments.md).

## Public API surface

```python
# col.equipment.vsg
def set_frequency(*, vsg_id: int, frequency: float) -> None
def set_power(*, vsg_id: int, power_dbm: float) -> None
def set_output(*, vsg_id: int, enabled: bool) -> None
def preset(*, vsg_id: int) -> None
def wait_complete(*, vsg_id: int) -> None
def set_alc(*, vsg_id: int, enabled: bool) -> None
def set_attenuation(*, vsg_id: int, attenuation_db: float) -> None
def upload_waveform(*, vsg_id: int, local_path: str, remote_name: str) -> None
def select_waveform(*, vsg_id: int, remote_name: str) -> None
def set_arb_state(*, vsg_id: int, enabled: bool) -> None
def configure_list(*, vsg_id: int, frequencies: list[float], powers: list[float] | None = None) -> None
def measure_output_state(*, vsg_id: int, key: str) -> float  # @measurement

# col.equipment.speca
def set_center_frequency(*, speca_id: int, frequency: float) -> None
def set_span(*, speca_id: int, span: float) -> None
def set_rbw(*, speca_id: int, rbw: float) -> None
def peak_search(*, speca_id: int, marker: int = 1) -> None
def set_marker_frequency(*, speca_id: int, marker: int, frequency_hz: float) -> None
def measure_marker_power(*, speca_id: int, marker: int = 1, key: str) -> float  # @measurement
def verify_marker_power(*, key: str, expected_val: float, tolerance: float = 0.5, optional: bool = False) -> VerificationResult
def measure_marker_frequency(*, speca_id: int, marker: int = 1, key: str) -> float  # @measurement
def measure_trace_power_at_frequency(*, speca_id: int, frequency_hz: float, key: str, trace_path: str | None = None) -> float  # @measurement
def verify_trace_power_at_frequency(*, key: str, expected_val: float, tolerance: float = 0.5, optional: bool = False) -> VerificationResult
def save_trace_data(*, speca_id: int, path: str, trace: int = 1, include_frequency: bool = True) -> None
def preset(*, speca_id: int) -> None
def set_reference_level(*, speca_id: int, level_dbm: float) -> None
def single_sweep(*, speca_id: int) -> None
def save_screenshot(*, speca_id: int, path: str) -> None
def download_capture(*, speca_id: int, path: str, kind: str = "iq") -> None  # Tek RTSA only
def save_spectrogram(*, speca_id: int, path: str) -> None  # Tek RTSA only
def configure_trigger(*, speca_id: int, source: str = "IMM") -> None  # Tek RTSA only
```

SCPI escape hatch: `col.equipment.scpi.write/query/query_float` accept `vsg_id=` or `speca_id=`.

## Model selection

| model | kind | Class |
|-------|------|-------|
| omitted / `generic` | vsg | `GenericVSG` |
| `keysight-esg` | vsg | `KeysightESGVSG` |
| omitted / `generic` | speca | `GenericSpecA` |
| `keysight-e4407b` | speca | `KeysightE4407BSpecA` |
| `tektronix-rsa5100b` | speca | `TektronixRSA5100BSpecA` |

## Capability errors

Drivers raise `EquipmentCapabilityError` when the configured model does not implement an operation. Examples:

| Operation | Supported on |
|-----------|----------------|
| `upload_waveform` | `keysight-esg` with E4438C IDN |
| `download_capture` | `tektronix-rsa5100b` only |
| `save_screenshot` | `keysight-e4407b` (not generic) |

## Artifacts

Large payloads use the artifact pattern ([ddd-database.md](ddd-database.md) §11.2):

| API | Artifact kind | Typical path |
|-----|---------------|--------------|
| `save_trace_data` | `speca_trace` | `traces/*.csv` |
| `save_screenshot` | `speca_screenshot` | `screens/*.png` |
| `download_capture` | `speca_capture` | `captures/*.bin` |
| `save_spectrogram` | `speca_spectrogram` | `spectrograms/*` |

## Binary SCPI

IQ upload and capture download use IEEE 488.2 definite-length blocks via `SCPIHelper.write_binary_block` / `read_binary_block` ([ddd-equipment-scpi.md](ddd-equipment-scpi.md)).

## Vendor manuals (implementation reference)

| Model slug | Manual |
|------------|--------|
| `keysight-esg` | E4428C/E4438C E4400-90506 |
| `keysight-e4407b` | E4407B E4401-90507 Vol. 1 |
| `tektronix-rsa5100b` | RSA5100B 077-0901-05 |

## References

- [ddd-equipment-dmm-psu.md](ddd-equipment-dmm-psu.md)
- [ddd-equipment-scpi.md](ddd-equipment-scpi.md)
- [ffo-laboratory-equipment.md](../features/ffo-laboratory-equipment.md)
- User guide: `docs/sphinx/source/guides/rf_equipment.rst`
