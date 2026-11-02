"""Create and finalize patient visit notes."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appointment, Encounter, EncounterAddendum, Patient
from backend.schemas import EncounterAddendumCreate, EncounterCreate, EncounterUpdate


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


def apply_encounter_update(
    session: Session,
    encounter_id: int,
    encounter_data: EncounterUpdate,
) -> Encounter:
    """Keep an appointment-linked visit note on its original visit date."""
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(status_code=409, detail="Finalized visit notes cannot be edited.")

    if (
        encounter.appointment_id is not None
        and encounter_data.visit_date != encounter.visit_date
    ):
        raise HTTPException(
            status_code=409,
            detail="A visit note linked to an appointment cannot change its visit date.",
        )

    for field, value in encounter_data.model_dump().items():
        setattr(encounter, field, value)
    return encounter


def finalize_encounter(session: Session, encounter_id: int) -> Encounter:
    """Finalize an assessed and planned draft visit note."""
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(status_code=409, detail="Visit note is already finalized.")
    if not encounter.assessment or not encounter.plan:
        raise HTTPException(
            status_code=409,
            detail="Assessment and plan are required to finalize a visit note.",
        )

    encounter.finalized_at = datetime.now(timezone.utc)
    return encounter


def create_encounter_addendum(
    session: Session, encounter_id: int, addendum_data: EncounterAddendumCreate
) -> EncounterAddendum:
    """Add a new entry without changing a finalized note's original content."""
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is None:
        raise HTTPException(
            status_code=409, detail="Finalize the visit note before adding an addendum."
        )

    addendum = EncounterAddendum(
        encounter_id=encounter_id, **addendum_data.model_dump()
    )
    session.add(addendum)
    session.flush()
    return addendum
