"""Create patient visit notes, optionally associated with an appointment."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appointment, Encounter, Patient
from backend.schemas import EncounterCreate


def create_encounter(
    session: Session,
    patient_id: int,
    encounter_data: EncounterCreate,
) -> Encounter:
    """Save a note without changing appointment lifecycle state."""
    patient_query = select(Patient).where(Patient.id == patient_id)
    if encounter_data.appointment_id is not None:
        # The appointment state transitions use this same parent-row lock.
        patient_query = patient_query.with_for_update()

    if session.scalar(patient_query) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    if encounter_data.appointment_id is not None:
        appointment = session.get(Appointment, encounter_data.appointment_id)
        if appointment is None or appointment.patient_id != patient_id:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if appointment.status not in ("checked_in", "completed"):
            raise HTTPException(
                status_code=409,
                detail="Only checked-in or completed appointments can have linked notes.",
            )
        if appointment.scheduled_date != encounter_data.visit_date:
            raise HTTPException(
                status_code=409,
                detail="Visit date must match the appointment date.",
            )

        existing_id = session.scalar(
            select(Encounter.id).where(
                Encounter.appointment_id == appointment.id
            )
        )
        if existing_id is not None:
            raise HTTPException(
                status_code=409,
                detail="This appointment already has a visit note.",
            )

    encounter = Encounter(
        patient_id=patient_id, **encounter_data.model_dump()
    )
    session.add(encounter)
    return encounter
