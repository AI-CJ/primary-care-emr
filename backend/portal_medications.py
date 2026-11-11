"""Medication summaries for the patient portal preview."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Medication, Patient
from backend.schemas import PortalMedicationSummary


def list_portal_preview_medications(
    session: Session, patient_id: int
) -> list[PortalMedicationSummary]:
    """Return displayed medication fields without staff chart identifiers."""
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = session.execute(
        select(
            Medication.id,
            Medication.name,
            Medication.strength,
            Medication.dose,
            Medication.frequency,
            Medication.status,
            Medication.start_date,
            Medication.end_date,
            Medication.instructions,
        )
        .where(Medication.patient_id == patient_id)
        .order_by(Medication.status, Medication.name, Medication.id)
    )
    return [
        PortalMedicationSummary(
            id=medication_id,
            name=name,
            strength=strength,
            dose=dose,
            frequency=frequency,
            status=status,
            start_date=start_date,
            end_date=end_date,
            instructions=instructions,
        )
        for (
            medication_id, name, strength, dose, frequency, status,
            start_date, end_date, instructions,
        ) in rows
    ]
