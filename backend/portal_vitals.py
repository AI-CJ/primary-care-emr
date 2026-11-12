"""Recent chart measurements for the staff portal preview."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Patient, Vital
from backend.schemas import PortalVitalSummary


def list_portal_preview_vitals(
    session: Session, patient_id: int
) -> list[PortalVitalSummary]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = session.execute(
        select(
            Vital.id,
            Vital.recorded_on,
            Vital.systolic_bp,
            Vital.diastolic_bp,
            Vital.heart_rate,
            Vital.respiratory_rate,
            Vital.temperature_c,
            Vital.oxygen_saturation,
            Vital.height_cm,
            Vital.weight_kg,
        )
        .where(Vital.patient_id == patient_id)
        .order_by(Vital.recorded_on.desc(), Vital.id.desc())
        .limit(3)
    )
    return [
        PortalVitalSummary(
            id=vital_id,
            recorded_on=recorded_on,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            heart_rate=heart_rate,
            respiratory_rate=respiratory_rate,
            temperature_c=temperature_c,
            oxygen_saturation=oxygen_saturation,
            height_cm=height_cm,
            weight_kg=weight_kg,
        )
        for (
            vital_id, recorded_on, systolic_bp, diastolic_bp, heart_rate,
            respiratory_rate, temperature_c, oxygen_saturation, height_cm,
            weight_kg,
        ) in rows
    ]
