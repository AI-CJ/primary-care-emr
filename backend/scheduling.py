"""Appointment overlap checks for the synthetic patient scheduler."""

from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appointment
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
