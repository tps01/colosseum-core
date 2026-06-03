from __future__ import annotations

from colosseum.decorators import MeasurementSource, VerificationResult, measurement, verification

from colosseum_equipment.api._verify import verify_tolerance
from colosseum_equipment.connections import get_cached_instrument


def set_attenuation_db(*, attn_id: int, attenuation_db: float) -> None:
    get_cached_instrument("attn", attn_id).set_attenuation_db(attenuation_db)


def preset(*, attn_id: int) -> None:
    get_cached_instrument("attn", attn_id).preset()


@measurement
def measure_attenuation_db(*, attn_id: int, key: str) -> float:
    return get_cached_instrument("attn", attn_id).measure_attenuation_db()


@verification(sources=[MeasurementSource(domain="equipment", command="measure_attenuation_db")])
def verify_attenuation_db(
    *,
    key: str,
    expected_val: float,
    tolerance: float = 0.1,
    optional: bool = False,
) -> VerificationResult:
    return verify_tolerance(
        domain="equipment",
        command="measure_attenuation_db",
        key=key,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )
