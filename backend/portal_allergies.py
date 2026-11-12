"""Allergy summaries for the patient portal preview."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Allergy, Patient
from backend.schemas import PortalAllergySummary


def list_portal_preview_allergies(
    session: Session, patient_id: int
) -> list[PortalAllergySummary]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = session.execute(
        select(
            Allergy.id,
            Allergy.allergen,
            Allergy.reaction,
            Allergy.severity,
            Allergy.status,
            Allergy.onset_date,
        )
        .where(Allergy.patient_id == patient_id)
        .order_by(Allergy.status, Allergy.allergen, Allergy.id)
    )
    return [
        PortalAllergySummary(
            id=allergy_id,
            allergen=allergen,
            reaction=reaction,
            severity=severity,
            status=status,
            onset_date=onset_date,
        )
        for allergy_id, allergen, reaction, severity, status, onset_date in rows
    ]
