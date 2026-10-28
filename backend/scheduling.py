"""Appointment overlap checks for the synthetic patient scheduler."""

from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appointment, Patient
from backend.schemas import AppointmentCreate


def ensure_appointment_slot_open(
    session: Session,
    patient_id: int,
    appointment_data: AppointmentCreate,
    *,
    exclude_appointment_id: int | None = None,
) -> None:
    """Check non-cancelled visits for this patient.

    The caller must lock the parent patient row with FOR UPDATE before
    checking and writing, so concurrent requests do not double-book them.
    """
    if appointment_data.status == "cancelled":
        return

    proposed_start = datetime.combine(
        appointment_data.scheduled_date, appointment_data.start_time
    )
    proposed_end = proposed_start + timedelta(
        minutes=appointment_data.duration_minutes
    )

    # An appointment lasting up to three hours can cross midnight.
    ordinal = appointment_data.scheduled_date.toordinal()
    first_day = date.fromordinal(max(1, ordinal - 1))
    last_day = date.fromordinal(min(date.max.toordinal(), ordinal + 1))

    query = select(Appointment).where(
        Appointment.patient_id == patient_id,
        Appointment.status != "cancelled",
        Appointment.scheduled_date.between(first_day, last_day),
    )
    if exclude_appointment_id is not None:
        query = query.where(Appointment.id != exclude_appointment_id)

    for existing in session.scalars(query):
        existing_start = datetime.combine(
            existing.scheduled_date, existing.start_time
        )
        existing_end = existing_start + timedelta(
            minutes=existing.duration_minutes
        )
        if proposed_start < existing_end and existing_start < proposed_end:
            raise HTTPException(
                status_code=409,
                detail="This patient already has an appointment during that time.",
            )


_ALLOWED_APPOINTMENT_TRANSITIONS = {
    "scheduled": {"scheduled", "checked_in", "cancelled"},
    "checked_in": {"checked_in", "completed", "cancelled"},
    "completed": {"completed"},
    "cancelled": {"cancelled"},
}


def ensure_appointment_status_transition(current: str, requested: str) -> None:
    """Prevent a finished or cancelled visit from silently reopening."""
    if requested not in _ALLOWED_APPOINTMENT_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change appointment status from {current} to {requested}.",
        )


def check_in_appointment(session: Session, appointment_id: int) -> Appointment:
    """Check in one scheduled visit under the patient's scheduling lock."""
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Use the same parent-row lock as scheduling and rescheduling.
    patient_id = session.scalar(
        select(Patient.id)
        .where(Patient.id == appointment.patient_id)
        .with_for_update()
    )
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Refresh after locking, so a concurrent edit cannot race this change.
    session.refresh(appointment)
    if appointment.status != "scheduled":
        raise HTTPException(
            status_code=409,
            detail="Only scheduled appointments can be checked in.",
        )

    ensure_appointment_status_transition(appointment.status, "checked_in")
    appointment.status = "checked_in"
    return appointment


def complete_appointment(session: Session, appointment_id: int) -> Appointment:
    """Complete one checked-in visit under the patient's scheduling lock."""
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    patient_id = session.scalar(
        select(Patient.id)
        .where(Patient.id == appointment.patient_id)
        .with_for_update()
    )
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Recheck status after locking to prevent concurrent completion or cancellation.
    session.refresh(appointment)
    if appointment.status != "checked_in":
        raise HTTPException(
            status_code=409,
            detail="Only checked-in appointments can be completed.",
        )

    ensure_appointment_status_transition(appointment.status, "completed")
    appointment.status = "completed"
    return appointment
